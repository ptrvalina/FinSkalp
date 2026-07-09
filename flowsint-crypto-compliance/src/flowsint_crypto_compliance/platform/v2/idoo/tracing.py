"""RFC-0021 Ch.11 — correlation ID propagation descriptor."""

from __future__ import annotations

from typing import Any


def tracing_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 11,
        "correlation_header": "X-Correlation-ID",
        "latency_header": "X-Finskalp-Latency-Ms",
        "propagation": {
            "http_inbound": "Read X-Correlation-ID from request or generate UUID4",
            "http_outbound": "Forward X-Correlation-ID to downstream services",
            "celery": "Pass correlation_id in task kwargs / headers",
            "database": "Include correlation_id in audit log entries",
        },
        "w3c_trace_context": {
            "traceparent": True,
            "tracestate": False,
        },
        "opentelemetry": {
            "enabled": True,
            "service_name": "finskalp-platform",
            "exporter": "grpc",
            "endpoint": "http://otel-collector:4317",
        },
        "platform_v2_pattern": {
            "routes": "request.headers.get('X-Correlation-ID')",
            "response": "X-Finskalp-Latency-Ms in response headers",
        },
        "principle_ru": "Распространение correlation ID через HTTP, Celery и аудит",
    }
