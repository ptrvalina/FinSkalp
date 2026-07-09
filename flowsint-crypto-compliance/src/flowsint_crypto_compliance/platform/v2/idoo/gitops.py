"""RFC-0021 Ch.6 — GitOps principles manifest."""

from __future__ import annotations

from typing import Any


def gitops_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 6,
        "principles": [
            "declarative_configuration",
            "git_as_single_source_of_truth",
            "automated_reconciliation",
            "pull_based_deployment",
            "continuous_observability",
        ],
        "principles_ru": {
            "declarative_configuration": "Декларативная конфигурация в Git",
            "git_as_single_source_of_truth": "Git — единый источник истины",
            "automated_reconciliation": "Автоматическая сверка желаемого и фактического состояния",
            "pull_based_deployment": "Pull-based развёртывание агентом",
            "continuous_observability": "Непрерывная наблюдаемость изменений",
        },
        "tools": {
            "current": ["docker-compose", "Makefile", "GitHub Actions"],
            "target": {
                "tool": "ArgoCD",
                "technical_debt": "TD-IDOO-2",
            },
        },
        "repositories": {
            "application": "flowsint (monorepo)",
            "infrastructure": "flowsint (docker-compose + Makefile)",
        },
        "principle_ru": "GitOps — Git как единый источник истины, автоматическая сверка состояния",
    }
