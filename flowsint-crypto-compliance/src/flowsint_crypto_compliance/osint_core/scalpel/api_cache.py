"""Redis / in-memory кэш ответов публичных API (TTL по типу источника)."""

from __future__ import annotations

import json
import os
import time
from typing import Any

_DEFAULT_TTL = {
    "sanctions": 86_400,
    "onchain": 3_600,
    "abuse": 21_600,
    "dns": 43_200,
    "default": 7_200,
}

_memory: dict[str, tuple[float, str]] = {}


def _redis_client():
    try:
        import redis

        url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        return redis.from_url(url, decode_responses=True)
    except Exception:
        return None


def cache_get(key: str) -> str | None:
    r = _redis_client()
    if r:
        try:
            val = r.get(f"finskalp:scalpel:{key}")
            return val if isinstance(val, str) else None
        except Exception:
            pass
    entry = _memory.get(key)
    if entry and entry[0] > time.time():
        return entry[1]
    return None


def cache_set(key: str, value: str, *, category: str = "default") -> None:
    ttl = _DEFAULT_TTL.get(category, _DEFAULT_TTL["default"])
    r = _redis_client()
    if r:
        try:
            r.setex(f"finskalp:scalpel:{key}", ttl, value)
            return
        except Exception:
            pass
    _memory[key] = (time.time() + ttl, value)


async def cached_fetch(
    gateway: Any,
    url: str,
    *,
    cache_key: str,
    category: str = "default",
    route: str = "clearnet",
) -> tuple[int, str, str]:
    cached = cache_get(cache_key)
    if cached is not None:
        return 200, cached, "cache"
    code, body, used_route = await gateway.fetch(url, route=route)
    if code == 200 and body:
        cache_set(cache_key, body, category=category)
    return code, body, used_route


def cache_stats() -> dict[str, Any]:
    return {
        "backend": "redis" if _redis_client() else "memory",
        "memory_keys": len(_memory),
    }
