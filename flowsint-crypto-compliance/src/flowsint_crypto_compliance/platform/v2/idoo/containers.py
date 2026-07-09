"""RFC-0021 Ch.3 — container requirements manifest."""

from __future__ import annotations

from typing import Any


def containers_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 3,
        "images": [
            {
                "name": "flowsint-api",
                "dockerfile": "flowsint-api/Dockerfile",
                "targets": ["dev", "prod"],
                "port": 5001,
                "healthcheck": "curl -f http://localhost:5001/health",
                "base_image": "python:3.12-slim",
            },
            {
                "name": "flowsint-app",
                "dockerfile": "flowsint-app/Dockerfile",
                "targets": ["prod"],
                "port": 80,
                "dev_dockerfile": "flowsint-app/Dockerfile.dev",
                "dev_port": 5173,
            },
            {
                "name": "flowsint-celery",
                "dockerfile": "flowsint-api/Dockerfile",
                "targets": ["dev", "prod"],
                "command": "celery -A flowsint_core.core.celery worker",
                "healthcheck": "celery inspect ping",
            },
            {
                "name": "flowsint-core",
                "description": "Shared library — no standalone image",
                "package": "flowsint-core",
            },
        ],
        "requirements": {
            "non_root_user": True,
            "read_only_root_fs": False,
            "resource_limits": {"cpu": "2", "memory": "4Gi"},
            "image_tag_policy": "semver or git-sha",
            "scan_on_build": True,
        },
        "principle_ru": "Контейнеры flowsint-api, flowsint-app, flowsint-core — неизменяемые образы с healthcheck",
    }
