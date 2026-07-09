"""RFC-0021 Ch.10 — structured log schema."""

from __future__ import annotations

from typing import Any


LOG_SCHEMA_FIELDS = [
    "timestamp",
    "service",
    "version",
    "level",
    "correlation_id",
    "trace_id",
    "span_id",
    "message",
    "user_id",
    "tenant_id",
    "request_id",
    "latency_ms",
    "status_code",
    "error",
]


def logging_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 10,
        "format": "json",
        "required_fields": LOG_SCHEMA_FIELDS,
        "field_descriptions": {
            "timestamp": "ISO 8601 UTC",
            "service": "Service name (flowsint-api, flowsint-celery, etc.)",
            "version": "Package version from pyproject.toml",
            "level": "DEBUG | INFO | WARNING | ERROR | CRITICAL",
            "correlation_id": "X-Correlation-ID header value",
            "trace_id": "OpenTelemetry trace ID",
            "span_id": "OpenTelemetry span ID",
            "message": "Human-readable log message",
            "user_id": "Authenticated user ID (if applicable)",
            "tenant_id": "Tenant scope",
            "request_id": "Unique request identifier",
            "latency_ms": "Request duration in milliseconds",
            "status_code": "HTTP status code",
            "error": "Error details object (if any)",
        },
        "sink": {
            "stdout": True,
            "loki": {"enabled": False, "technical_debt": "TD-IDOO-4"},
        },
        "principle_ru": "Структурированные логи JSON — timestamp, service, version, correlation_id",
    }
