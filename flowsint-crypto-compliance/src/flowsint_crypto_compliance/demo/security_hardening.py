"""Настройки безопасности демо-стенда."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from flowsint_crypto_compliance.osint_core.scalpel.security import (
    assert_upload_size,
    is_safe_external_url,
    sanitize_filename,
    sanitize_spiderfoot_target,
    sanitize_username,
    validate_upload_magic,
)

__all__ = [
    "DemoRateLimitMiddleware",
    "assert_demo_api_token",
    "assert_upload_size",
    "cors_origins_from_env",
    "demo_api_token_from_env",
    "demo_bind_host",
    "is_safe_external_url",
    "sanitize_filename",
    "sanitize_spiderfoot_target",
    "sanitize_username",
    "validate_case_ref",
    "validate_evidence_hash",
    "validate_upload_magic",
]

_RATE_LIMIT_PATHS = frozenset(
    {
        "/api/v1/score",
        "/status",
        "/api/ocr/extract",
        "/api/wallet/screen",
        "/api/kyt/watchlist",
        "/api/finskalp/investigate",
        "/api/osint/investigate",
        "/api/osint/source-reliability/feedback",
        "/api/osint/continuous/rescan",
    }
)


class DemoRateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-process rate limit for sensitive public demo endpoints."""

    def __init__(self, app, *, rps: float | None = None, burst: int | None = None):
        super().__init__(app)
        self._rps = rps or float(os.getenv("FINSKALP_DEMO_RATE_LIMIT_RPS", "10"))
        self._burst = burst or int(os.getenv("FINSKALP_DEMO_RATE_LIMIT_BURST", "20"))
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        return forwarded or (request.client.host if request.client else "unknown")

    def _limited_path(self, path: str) -> bool:
        if path in _RATE_LIMIT_PATHS:
            return True
        if path.startswith("/api/v1/score/"):
            return True
        return False

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "GET" and path == "/status":
            pass  # always rate-limit status
        elif request.method not in ("GET", "POST", "PATCH"):
            return await call_next(request)

        if not self._limited_path(path):
            return await call_next(request)

        key = self._client_key(request)
        now = time.monotonic()
        window = 1.0
        with self._lock:
            hits = [t for t in self._buckets[key] if now - t < window]
            if len(hits) >= self._burst:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded — retry later"},
                    headers={"Retry-After": "1"},
                )
            hits.append(now)
            self._buckets[key] = hits

        return await call_next(request)


def cors_origins_from_env() -> list[str]:
    raw = os.getenv("FINSKALP_CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    if os.getenv("COMPLIANCE_DEMO_ALLOW_ALL_CORS", "0") == "1":
        return ["*"]
    port = os.getenv("COMPLIANCE_DEMO_PORT", "8877")
    return [f"http://localhost:{port}", f"http://127.0.0.1:{port}"]


def demo_bind_host() -> str:
    return os.getenv("COMPLIANCE_DEMO_BIND_HOST", "127.0.0.1")


def validate_evidence_hash(content_hash: str) -> str:
    """SHA-256 prefix for evidence lookup — hex only, no path traversal."""
    h = (content_hash or "").strip().lower()
    if not h or len(h) > 64 or not all(c in "0123456789abcdef" for c in h):
        raise ValueError("invalid evidence hash")
    return h


def validate_case_ref(case_ref: str) -> str:
    ref = (case_ref or "").strip()
    if not ref or len(ref) > 128:
        raise ValueError("invalid case_ref")
    if ".." in ref or "/" in ref or "\\" in ref:
        raise ValueError("invalid case_ref")
    return ref


def demo_api_token_from_env() -> str | None:
    token = os.getenv("FINSKALP_DEMO_API_TOKEN", "").strip()
    return token or None


def assert_demo_api_token(request) -> None:
    """When FINSKALP_DEMO_API_TOKEN is set, mutating endpoints require Authorization: Bearer <token>."""
    expected = demo_api_token_from_env()
    if not expected:
        return
    auth = (request.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        provided = auth[7:].strip()
    else:
        provided = request.headers.get("x-finskalp-token", "").strip()
    if provided != expected:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Требуется токен демо-API")
