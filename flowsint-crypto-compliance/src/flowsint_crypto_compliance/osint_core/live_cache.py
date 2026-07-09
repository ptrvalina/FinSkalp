"""Redis/in-memory JSON cache для live collectors."""

from __future__ import annotations

import json
import os
import time
from typing import Any

_TTL = {
    "onchain_live": 300,       # 5 min
    "sanctions_live": 86_400,  # 24 h
    "maigret_live": 3_600,     # 1 h
    "abuse_live": 21_600,
    "ahmia_live": 7_200,
    "default": 600,
}

_memory: dict[str, tuple[float, str]] = {}


def _redis():
    try:
        import redis

        url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        return redis.from_url(url, decode_responses=True)
    except Exception:
        return None


def cache_get_json(key: str) -> dict[str, Any] | None:
    r = _redis()
    if r:
        try:
            raw = r.get(f"finskalp:live:{key}")
            if raw:
                return json.loads(raw)
        except Exception:
            pass
    entry = _memory.get(key)
    if entry and entry[0] > time.time():
        return json.loads(entry[1])
    return None


def cache_set_json(key: str, value: dict[str, Any], *, category: str = "default") -> None:
    raw = json.dumps(value, ensure_ascii=False)
    ttl = _TTL.get(category, _TTL["default"])
    r = _redis()
    if r:
        try:
            r.setex(f"finskalp:live:{key}", ttl, raw)
            return
        except Exception:
            pass
    _memory[key] = (time.time() + ttl, raw)
