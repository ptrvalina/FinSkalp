"""RFC-0010 Ch.19 — API latency measurement."""

from __future__ import annotations

import time
from typing import Any, Callable


def with_latency_ms(fn: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any) -> dict[str, Any]:
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    if isinstance(result, dict) and "latency_ms" not in result:
        result["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    return result


def latency_headers(body: dict[str, Any]) -> dict[str, str]:
    ms = body.get("latency_ms")
    if ms is None:
        return {}
    return {"X-Finskalp-Latency-Ms": str(ms)}
