"""RFC-0021 Ch.1 — infrastructure principles manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.idoo.types import InfraPrinciple


def principles_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0021",
        "chapter": 1,
        "principles": [p.value for p in InfraPrinciple],
        "principles_ru": {
            InfraPrinciple.INFRASTRUCTURE_AS_CODE.value: "Инфраструктура как код — декларативное описание",
            InfraPrinciple.GITOPS_SINGLE_SOURCE.value: "GitOps — Git как единый источник истины",
            InfraPrinciple.IMMUTABLE_ARTIFACTS.value: "Неизменяемые артефакты сборки",
            InfraPrinciple.OBSERVABILITY_BY_DEFAULT.value: "Наблюдаемость по умолчанию",
            InfraPrinciple.AUTOMATED_RECOVERY.value: "Автоматическое восстановление",
            InfraPrinciple.LEAST_PRIVILEGE_ACCESS.value: "Минимальные привилегии доступа",
            InfraPrinciple.SECRETS_NEVER_IN_CODE.value: "Секреты никогда не в коде",
            InfraPrinciple.ENVIRONMENT_PARITY.value: "Паритет окружений dev/stage/prod",
        },
        "principle_ru": "Инфраструктура как код, GitOps и наблюдаемость по умолчанию",
    }
