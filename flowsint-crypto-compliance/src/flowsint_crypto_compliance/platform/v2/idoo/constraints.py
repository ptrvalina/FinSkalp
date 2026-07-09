"""RFC-0021 Ch.19 — forbidden infrastructure practices."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.idoo.types import InfraPrinciple

_FORBIDDEN_PRACTICES = frozenset({
    "manual_production_changes",
    "secrets_in_git",
    "unpinned_container_images",
    "skip_health_checks",
    "deploy_without_tests",
    "shared_prod_credentials",
    "disable_backup",
    "run_as_root_in_prod",
    "expose_database_publicly",
    "disable_audit_logging",
})


def constraints_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 19,
        "principles": [p.value for p in InfraPrinciple],
        "forbidden_practices": sorted(_FORBIDDEN_PRACTICES),
        "forbidden_practices_ru": {
            "manual_production_changes": "Ручные изменения в production",
            "secrets_in_git": "Секреты в Git-репозитории",
            "unpinned_container_images": "Незакреплённые образы контейнеров (:latest без контроля)",
            "skip_health_checks": "Пропуск health-check",
            "deploy_without_tests": "Развёртывание без тестов",
            "shared_prod_credentials": "Общие учётные данные production",
            "disable_backup": "Отключение резервного копирования",
            "run_as_root_in_prod": "Запуск от root в production",
            "expose_database_publicly": "Публичный доступ к БД",
            "disable_audit_logging": "Отключение аудит-логирования",
        },
        "enforcement": {
            "ci_gates": "tests must pass before merge",
            "pre_commit": "secret scanning",
            "compose": "healthcheck on all services",
        },
        "principle_ru": "Запрещённые практики инфраструктуры — секреты в Git, ручные prod-изменения",
    }


def assert_infra_constraint(practice: str) -> None:
    if practice in _FORBIDDEN_PRACTICES:
        raise ValueError(f"Forbidden infrastructure practice: {practice}")
