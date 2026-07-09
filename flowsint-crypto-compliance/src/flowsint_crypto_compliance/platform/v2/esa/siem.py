"""RFC-0020 Ch.14 — SIEM export stubs."""

from __future__ import annotations

from typing import Any


def siem_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 14,
        "exports": {
            "syslog": {
                "enabled": False,
                "protocol": "TLS syslog (RFC 5424)",
                "host": "siem.flowsint.local",
                "port": 6514,
                "format": "CEF",
                "technical_debt": "TD-ESA-4",
            },
            "opentelemetry": {
                "enabled": True,
                "endpoint": "http://otel-collector:4317",
                "protocol": "grpc",
                "signals": ["traces", "metrics", "logs"],
                "resource_attributes": {
                    "service.name": "finskalp-platform",
                    "deployment.environment": "production",
                },
            },
            "webhook": {
                "enabled": False,
                "url": "",
                "auth": "bearer_token",
                "events": [
                    "security.login.failed",
                    "security.access.denied",
                    "security.role.changed",
                    "security.integrity.violation",
                ],
                "technical_debt": "TD-ESA-4",
            },
        },
        "event_mapping": {
            "login": "auth.login",
            "access_denied": "authz.denied",
            "role_change": "iam.role_change",
            "export": "data.export",
            "integrity_violation": "evidence.integrity_fail",
        },
        "principle_ru": "Экспорт событий безопасности в SIEM — syslog, OpenTelemetry, webhook",
    }
