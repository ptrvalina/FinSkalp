from __future__ import annotations

import os

from sqlalchemy.orm import Session

from flowsint_crypto_compliance.storage.label_cache import LabelCache
from flowsint_crypto_compliance.storage.postgres_label_cache import PostgresLabelCache
from flowsint_crypto_compliance.storage.redis_label_cache import RedisLabelCache


def build_label_cache(db: Session) -> LabelCache:
    """Production label cache with optional Redis hot tier."""
    pg = PostgresLabelCache(db)
    if os.getenv("REDIS_URL"):
        return RedisLabelCache(pg)
    return pg
