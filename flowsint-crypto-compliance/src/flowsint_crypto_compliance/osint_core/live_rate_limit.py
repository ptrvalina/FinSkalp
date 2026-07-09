"""Rate limit per external source — max 5 req/sec (200ms interval)."""

from __future__ import annotations

import asyncio
import time

_MIN_INTERVAL = 0.2  # 5 req/sec
_last: dict[str, float] = {}
_lock = asyncio.Lock()


async def await_rate_limit(source: str) -> None:
    async with _lock:
        now = time.monotonic()
        prev = _last.get(source, 0.0)
        wait = _MIN_INTERVAL - (now - prev)
        if wait > 0:
            await asyncio.sleep(wait)
        _last[source] = time.monotonic()
