"""RFC-0015 Ch.14 — caching for immutable registry data."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any


class RegistryCache:
    """In-memory TTL cache for immutable registry snapshots."""

    def __init__(self, *, default_ttl_seconds: int = 3600) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl_seconds
        self._hits = 0
        self._misses = 0

    def _key(self, connector_id: str, query: dict[str, Any] | None) -> str:
        raw = json.dumps({"connector_id": connector_id, "query": query or {}}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, connector_id: str, query: dict[str, Any] | None = None) -> Any | None:
        key = self._key(connector_id, query)
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        value, expires = entry
        if time.time() > expires:
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return value

    def set(
        self,
        connector_id: str,
        query: dict[str, Any] | None,
        value: Any,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        key = self._key(connector_id, query)
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        self._store[key] = (value, time.time() + ttl)

    def stats(self) -> dict[str, Any]:
        return {
            "entries": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(1, self._hits + self._misses), 4),
        }

    def clear(self) -> None:
        self._store.clear()


_cache: RegistryCache | None = None


def get_registry_cache() -> RegistryCache:
    global _cache
    if _cache is None:
        _cache = RegistryCache()
    return _cache
