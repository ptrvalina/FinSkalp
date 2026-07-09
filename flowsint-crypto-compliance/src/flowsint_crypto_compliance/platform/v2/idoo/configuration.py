"""RFC-0021 Ch.7 — environment configuration layers."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.idoo.types import Environment


def configuration_manifest() -> dict[str, Any]:
    layers = {
        Environment.DEV.value: {
            "compose": "docker-compose.dev.yml",
            "env_files": [".env", "flowsint-api/.env"],
            "secrets": "MASTER_VAULT_KEY_V1 (dev key)",
            "database": "postgresql://flowsint:flowsint@postgres:5432/flowsint",
            "debug": True,
        },
        Environment.TEST.value: {
            "compose": None,
            "env_files": [],
            "secrets": "in-memory / dummy",
            "database": "sqlite or memory",
            "debug": True,
        },
        Environment.STAGE.value: {
            "compose": "docker-compose.prod.yml",
            "env_files": [".env"],
            "secrets": "vault (staging)",
            "database": "managed postgres",
            "debug": False,
        },
        Environment.PROD.value: {
            "compose": "docker-compose.prod.yml",
            "env_files": [],
            "secrets": "vault (production)",
            "database": "managed postgres HA",
            "debug": False,
        },
    }
    return {
        "rfc": "RFC-0021",
        "chapter": 7,
        "environments": [e.value for e in Environment],
        "layers": layers,
        "secrets_management": {
            "provider": "flowsint vault",
            "env_var": "MASTER_VAULT_KEY_V1",
            "never_in_code": True,
            "rotation_policy": "90_days",
        },
        "principle_ru": "Конфигурация по слоям окружений — секреты через vault, не в коде",
    }
