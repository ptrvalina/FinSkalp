"""Rate limiting for flowsint-api (:5001) — opt-in via FINSKALP_API_RATE_LIMIT_ENABLED."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def api_rate_limit_enabled() -> bool:
    raw = os.getenv("FINSKALP_API_RATE_LIMIT_ENABLED", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


class ApiRateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket style limiter for authenticated API plane."""

    def __init__(self, app, *, rps: float | None = None, burst: int | None = None):
        super().__init__(app)
        self._rps = rps or float(os.getenv("FINSKALP_API_RATE_LIMIT_RPS", "30"))
        self._burst = burst or int(os.getenv("FINSKALP_API_RATE_LIMIT_BURST", "60"))
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        auth = request.headers.get("authorization", "")[:32]
        ip = forwarded or (request.client.host if request.client else "unknown")
        return f"{ip}:{auth}"

    def _skip(self, path: str) -> bool:
        if path in ("/health", "/metrics", "/docs", "/openapi.json", "/redoc"):
            return True
        return path.startswith("/api/auth/login") or path.startswith("/api/auth/register")

    async def dispatch(self, request: Request, call_next):
        if not api_rate_limit_enabled():
            return await call_next(request)
        path = request.url.path
        if self._skip(path):
            return await call_next(request)

        key = self._client_key(request)
        now = time.monotonic()
        with self._lock:
            hits = [t for t in self._buckets[key] if now - t < 1.0]
            if len(hits) >= self._burst:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "API rate limit exceeded"},
                    headers={"Retry-After": "1"},
                )
            hits.append(now)
            self._buckets[key] = hits
        return await call_next(request)
