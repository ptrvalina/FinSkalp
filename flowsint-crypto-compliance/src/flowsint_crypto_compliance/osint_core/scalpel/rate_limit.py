"""Per-collector rate limiting (in-process + optional Redis)."""

from __future__ import annotations

import os
import time
from typing import Any

_LIMITS: dict[str, float] = {
    "onchain_explorer": 2.0,
    "sanctions_watchlist": 1.0,
    "username_social": 3.0,
    "abuse_scam_registry": 1.5,
    "darknet_index": 2.0,
    "vasp_registry": 5.0,
    "court_enforcement": 2.0,
    "reverse_whois_dns": 2.0,
}

_last_call: dict[str, float] = {}


def acquire(collector_id: str) -> bool:
    """Returns False if rate limit exceeded (caller should skip or wait)."""
    min_interval = _LIMITS.get(collector_id, float(os.getenv("FINSKALP_RATE_LIMIT_SEC", "1.0")))
    now = time.monotonic()
    prev = _last_call.get(collector_id, 0.0)
    if now - prev < min_interval:
        return False
    _last_call[collector_id] = now
    return True


def rate_limit_status() -> dict[str, Any]:
    return {"limits_sec": _LIMITS, "collectors": list(_LIMITS)}
