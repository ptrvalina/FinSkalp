"""RFC-0020 Ch.1 — Zero Trust constraints enforcement."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.esa.types import SecurityPrinciple

_FORBIDDEN_ACTIONS = frozenset({
    "bypass_authentication",
    "bypass_authorization",
    "bypass_audit_trail",
    "store_secrets_in_code",
    "disable_encryption",
    "cross_tenant_access",
    "modify_audit_log",
    "export_without_classification_check",
    "admin_without_mfa",
    "direct_knowledge_graph_mutation",
})


def zero_trust_constraints() -> dict[str, Any]:
    return {
        "principles": [p.value for p in SecurityPrinciple],
        "principles_ru": {
            SecurityPrinciple.VERIFY_EXPLICITLY.value: "Проверять каждый запрос явно",
            SecurityPrinciple.LEAST_PRIVILEGE.value: "Минимальные привилегии",
            SecurityPrinciple.ASSUME_BREACH.value: "Предполагать компрометацию",
            SecurityPrinciple.MICRO_SEGMENTATION.value: "Микросегментация сети",
            SecurityPrinciple.CONTINUOUS_VALIDATION.value: "Непрерывная валидация",
            SecurityPrinciple.ENCRYPT_EVERYWHERE.value: "Шифрование везде",
            SecurityPrinciple.AUDIT_EVERYTHING.value: "Аудит всех действий",
            SecurityPrinciple.NO_IMPLICIT_TRUST.value: "Нет неявного доверия",
        },
        "forbidden_actions": sorted(_FORBIDDEN_ACTIONS),
        "enforcement": {
            "authentication": "required_on_every_request",
            "authorization": "rbac_abac_per_resource",
            "encryption": "tls_1_2_minimum",
            "audit": "append_only_security_log",
            "network": "default_deny_service_mesh",
        },
        "principle_ru": "Zero Trust — никакого неявного доверия, проверка на каждом шаге",
    }


def assert_zero_trust(action: str) -> None:
    if action in _FORBIDDEN_ACTIONS:
        raise PermissionError(f"Zero Trust forbidden action: {action}")
