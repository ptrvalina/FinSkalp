"""RFC-0021 Ch.5 — CI/CD pipeline stages manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _github_workflows() -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[6]
    workflows_dir = root / ".github" / "workflows"
    workflows: list[dict[str, Any]] = []
    if workflows_dir.is_dir():
        for wf in sorted(workflows_dir.glob("*.yml")):
            workflows.append({
                "file": f".github/workflows/{wf.name}",
                "name": wf.stem,
            })
    return workflows


def cicd_manifest() -> dict[str, Any]:
    stages = [
        {"name": "checkout", "description": "Clone repository"},
        {"name": "install", "description": "uv sync / npm install"},
        {"name": "lint", "description": "ruff, mypy, eslint"},
        {"name": "test", "description": "pytest + vitest via make test"},
        {"name": "build", "description": "Docker image build"},
        {"name": "scan", "description": "Container vulnerability scan"},
        {"name": "publish", "description": "Push to container registry"},
        {"name": "deploy", "description": "GitOps sync or compose rollout"},
    ]
    return {
        "rfc": "RFC-0021",
        "chapter": 5,
        "stages": stages,
        "stage_count": len(stages),
        "github_workflows": _github_workflows(),
        "makefile_entrypoint": "make test",
        "compose_deploy": ["docker-compose.dev.yml", "docker-compose.prod.yml"],
        "principle_ru": "CI/CD — автоматическая сборка, тестирование и развёртывание через GitHub Actions",
    }
