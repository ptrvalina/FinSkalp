"""Tests for flowsint-api rate limiting middleware."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from flowsint_crypto_compliance.observability.api_rate_limit import (
    ApiRateLimitMiddleware,
    api_rate_limit_enabled,
)


async def _ok(_request: Request):
    return JSONResponse({"ok": True})


def _build_app(*, burst: int = 3) -> Starlette:
    app = Starlette(routes=[Route("/api/items", _ok), Route("/health", _ok)])
    app.add_middleware(ApiRateLimitMiddleware, rps=100, burst=burst)
    return app


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", True),
        ("true", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("", False),
    ],
)
def test_api_rate_limit_enabled(value: str, expected: bool) -> None:
    with patch.dict(os.environ, {"FINSKALP_API_RATE_LIMIT_ENABLED": value}, clear=False):
        assert api_rate_limit_enabled() is expected


@pytest.mark.asyncio
async def test_rate_limit_disabled_passes_through() -> None:
    with patch.dict(os.environ, {"FINSKALP_API_RATE_LIMIT_ENABLED": "0"}, clear=False):
        middleware = ApiRateLimitMiddleware(Starlette(), rps=100, burst=1)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/items",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

        for _ in range(5):
            response = await middleware.dispatch(request, call_next)

        assert call_next.await_count == 5
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_returns_429_when_burst_exceeded() -> None:
    with patch.dict(os.environ, {"FINSKALP_API_RATE_LIMIT_ENABLED": "1"}, clear=False):
        middleware = ApiRateLimitMiddleware(Starlette(), rps=100, burst=2)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/items",
            "headers": [],
            "client": ("10.0.0.1", 4321),
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

        await middleware.dispatch(request, call_next)
        await middleware.dispatch(request, call_next)
        blocked = await middleware.dispatch(request, call_next)

        assert call_next.await_count == 2
        assert blocked.status_code == 429
        assert blocked.body == b'{"detail":"API rate limit exceeded"}'


@pytest.mark.asyncio
async def test_rate_limit_skips_health_path() -> None:
    with patch.dict(os.environ, {"FINSKALP_API_RATE_LIMIT_ENABLED": "1"}, clear=False):
        middleware = ApiRateLimitMiddleware(Starlette(), rps=100, burst=1)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
            "client": ("10.0.0.2", 4322),
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

        for _ in range(5):
            response = await middleware.dispatch(request, call_next)

        assert call_next.await_count == 5
        assert response.status_code == 200
