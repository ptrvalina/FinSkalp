"""RFC-0021 Ch.17 — versioning, blue/green, canary deployment."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _read_pyproject_version(relative: str) -> str:
    try:
        root = Path(__file__).resolve().parents[6]
        pyproject = root / relative / "pyproject.toml"
        if pyproject.is_file():
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("version") and "=" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "unknown"


def versioning_manifest() -> dict[str, Any]:
    components = {
        "flowsint-api": _read_pyproject_version("flowsint-api"),
        "flowsint-core": _read_pyproject_version("flowsint-core"),
        "flowsint-types": _read_pyproject_version("flowsint-types"),
        "flowsint-enrichers": _read_pyproject_version("flowsint-enrichers"),
        "flowsint-crypto-compliance": _read_pyproject_version("flowsint-crypto-compliance"),
        "flowsint-app": _read_pyproject_version("flowsint-app") if Path(__file__).resolve().parents[6].joinpath("flowsint-app/pyproject.toml").is_file() else "n/a",
    }
    return {
        "rfc": "RFC-0021",
        "chapter": 17,
        "components": components,
        "platform_version": components.get("flowsint-api", "unknown"),
        "deployment_strategies": {
            "blue_green": {
                "enabled": False,
                "description": "Two identical environments, switch traffic on validation",
                "technical_debt": "TD-IDOO-1",
            },
            "canary": {
                "enabled": False,
                "description": "Gradual traffic shift to new version (5% → 25% → 100%)",
                "technical_debt": "TD-IDOO-1",
            },
            "rolling": {
                "enabled": True,
                "description": "docker compose up --no-deps -d api (current default)",
            },
        },
        "image_tag": "${FLOWSINT_VERSION:-latest}",
        "principle_ru": "Версионирование компонентов из pyproject, blue/green и canary — целевые стратегии",
    }
