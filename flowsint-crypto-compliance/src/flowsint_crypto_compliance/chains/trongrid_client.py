"""Shared TronGrid HTTP client — concurrency limit + exponential backoff."""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

_MAX_CONCURRENT = max(1, int(__import__("os").getenv("TRONGRID_MAX_CONCURRENT", "8")))
_BACKOFF_SEC = [0.5, 1.0, 2.0, 4.0, 8.0]

_semaphore: asyncio.Semaphore | None = None


def _sem() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
    return _semaphore


def trongrid_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"User-Agent": "FinSkalp-Live/1.0 (+regulatory OSINT)"}
    key = __import__("os").getenv("TRONGRID_API_KEY", "").strip()
    if key:
        headers["TRON-PRO-API-KEY"] = key
    if extra:
        headers.update(extra)
    return headers


async def trongrid_get(
    path: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 20.0,
    max_retries: int = 5,
) -> httpx.Response:
    """GET TRON REST path via configured :class:`OnChainProvider` (rate limit + backoff)."""
    from flowsint_crypto_compliance.chains.on_chain_provider import get_tron_provider

    provider = get_tron_provider()
    last: httpx.Response | None = None

    async with _sem():
        for attempt in range(max_retries):
            if attempt:
                delay = _BACKOFF_SEC[min(attempt - 1, len(_BACKOFF_SEC) - 1)]
                await asyncio.sleep(delay + random.uniform(0, 0.25))
            last = await provider.get(path, params=params, timeout=timeout)
            if last.status_code == 429 or last.status_code >= 500:
                continue
            return last
    assert last is not None
    return last
