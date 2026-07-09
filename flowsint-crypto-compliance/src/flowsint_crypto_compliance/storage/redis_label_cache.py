"""Redis hot cache in front of PostgreSQL sovereign registry."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from flowsint_types.fiat_crypto import Chain, SovereignRiskLabel

from .label_cache import LabelCache

if TYPE_CHECKING:
    from .postgres_label_cache import PostgresLabelCache

_DEFAULT_TTL = int(os.getenv("COMPLIANCE_REGISTRY_CACHE_TTL", "3600"))
_KEY_PREFIX = "compliance:registry:"


class RedisLabelCache(LabelCache):
    """Two-tier cache: Redis → PostgreSQL (via PostgresLabelCache)."""

    def __init__(self, backing: PostgresLabelCache, redis_url: str | None = None) -> None:
        super().__init__()
        self._backing = backing
        self._redis = self._connect(redis_url or os.getenv("REDIS_URL"))

    @staticmethod
    def _connect(url: str | None):
        if not url:
            return None
        try:
            import redis

            return redis.from_url(url, decode_responses=True)
        except Exception:
            return None

    def _cache_key(self, chain: Chain, address: str) -> str:
        normalized = address.lower() if chain == Chain.ETH else address
        return f"{_KEY_PREFIX}{chain.value}:{normalized}"

    def put(self, label: SovereignRiskLabel) -> None:
        self._backing.put(label)
        if self._redis:
            key = self._cache_key(label.chain, label.address)
            self._redis.setex(key, _DEFAULT_TTL, label.model_dump_json())

    def lookup(self, chain: Chain, address: str) -> SovereignRiskLabel | None:
        if self._redis:
            raw = self._redis.get(self._cache_key(chain, address))
            if raw:
                return SovereignRiskLabel.model_validate_json(raw)
        label = self._backing.lookup(chain, address)
        if label and self._redis:
            self._redis.setex(
                self._cache_key(chain, address),
                _DEFAULT_TTL,
                label.model_dump_json(),
            )
        return label

    def bulk_upsert(self, labels: list[SovereignRiskLabel]) -> int:
        count = self._backing.bulk_upsert(labels)
        if self._redis:
            pipe = self._redis.pipeline()
            for label in labels:
                pipe.setex(
                    self._cache_key(label.chain, label.address),
                    _DEFAULT_TTL,
                    label.model_dump_json(),
                )
            pipe.execute()
        return count

    def count(self) -> int:
        return self._backing.count()
