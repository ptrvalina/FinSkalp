"""FastAPI middleware — correlation ID propagation."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from flowsint_crypto_compliance.observability.logging import bind_correlation_id, get_logger

log = get_logger("http")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        bind_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        log.info(
            "request %s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
        )
        return response
