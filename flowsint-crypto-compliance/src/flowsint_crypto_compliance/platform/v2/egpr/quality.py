"""RFC-0022 Ch.10 — quality metrics."""

from __future__ import annotations

from typing import Any


def quality_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0022",
        "chapter": 10,
        "metrics": {
            "test_coverage": {
                "target_percent": 80,
                "current_percent": None,
                "status": "stub",
                "note": "Per-RFC test suites in flowsint-crypto-compliance/tests/",
            },
            "build_success_rate": {
                "target_percent": 99,
                "current_percent": 100.0,
                "status": "healthy",
                "ci_workflow": "finskalp-compliance.yml",
            },
            "api_stability": {
                "versioned_prefix": "/api/platform/v2",
                "breaking_change_policy": "semver major bump",
                "deprecation_window_days": 90,
                "status": "stable",
            },
        },
        "quality_gates": [
            "pytest pass",
            "ruff lint",
            "no secrets in diff",
            "RBAC on mutate routes",
        ],
        "rfc_test_count": 22,
        "principle_ru": "Метрики качества — покрытие тестами, сборки и стабильность API",
    }
