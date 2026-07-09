"""RFC-0020 Ch.10 — service mesh mTLS policies stub."""

from __future__ import annotations

from typing import Any


def service_mesh_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 10,
        "mesh": {
            "provider": "stub",
            "implementation": "Istio (planned)",
            "technical_debt": "TD-ESA-3",
        },
        "mtls": {
            "enabled": False,
            "mode": "STRICT",
            "ca_provider": "platform-internal-ca",
            "cert_rotation_days": 90,
            "required_services": [
                "flowsint-api",
                "flowsint-crypto-compliance",
                "flowsint-core-worker",
                "neo4j",
                "postgresql",
            ],
        },
        "policies": [
            {
                "name": "default-deny",
                "action": "DENY",
                "source": "*",
                "destination": "*",
                "unless": "mTLS + authorization",
            },
            {
                "name": "api-to-compliance",
                "action": "ALLOW",
                "source": "flowsint-api",
                "destination": "flowsint-crypto-compliance",
                "ports": [8000],
            },
            {
                "name": "worker-to-db",
                "action": "ALLOW",
                "source": "flowsint-core-worker",
                "destination": "postgresql",
                "ports": [5432],
            },
        ],
        "observability": {
            "tracing": "OpenTelemetry",
            "metrics": "Prometheus",
            "access_logs": True,
        },
        "principle_ru": "mTLS между всеми внутренними сервисами — Zero Trust mesh",
    }
