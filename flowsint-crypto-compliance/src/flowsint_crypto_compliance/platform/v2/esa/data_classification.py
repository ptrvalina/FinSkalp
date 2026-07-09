"""RFC-0020 Ch.6 — data classification rules."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.esa.types import DataClassification


def _rules_for(level: DataClassification) -> dict[str, Any]:
    base = {
        DataClassification.PUBLIC: {
            "storage": {"encryption_required": False, "at_rest": "optional", "backup_retention_days": 30},
            "transfer": {"tls_required": True, "min_tls_version": "1.2", "external_sharing": True},
            "logging": {"log_payload": True, "mask_pii": False, "retention_days": 90},
            "export": {"allowed_roles": ["analyst", "senior_analyst", "lead", "admin", "auditor"], "watermark": False},
        },
        DataClassification.INTERNAL: {
            "storage": {"encryption_required": True, "at_rest": "AES-256-GCM", "backup_retention_days": 180},
            "transfer": {"tls_required": True, "min_tls_version": "1.2", "external_sharing": False},
            "logging": {"log_payload": True, "mask_pii": True, "retention_days": 365},
            "export": {"allowed_roles": ["senior_analyst", "lead", "admin", "auditor"], "watermark": True},
        },
        DataClassification.CONFIDENTIAL: {
            "storage": {"encryption_required": True, "at_rest": "AES-256-GCM", "backup_retention_days": 365},
            "transfer": {"tls_required": True, "min_tls_version": "1.3", "external_sharing": False, "mtls_internal": True},
            "logging": {"log_payload": False, "mask_pii": True, "retention_days": 730},
            "export": {"allowed_roles": ["lead", "admin", "auditor"], "watermark": True, "approval_required": True},
        },
        DataClassification.RESTRICTED: {
            "storage": {"encryption_required": True, "at_rest": "AES-256-GCM+HSM", "backup_retention_days": 2555},
            "transfer": {"tls_required": True, "min_tls_version": "1.3", "external_sharing": False, "mtls_internal": True},
            "logging": {"log_payload": False, "mask_pii": True, "retention_days": 2555, "immutable": True},
            "export": {"allowed_roles": ["admin", "auditor"], "watermark": True, "approval_required": True, "dual_control": True},
        },
    }
    return base[level]


def classification_rules(level: DataClassification | str) -> dict[str, Any]:
    if isinstance(level, str):
        level = DataClassification(level)
    return {
        "classification": level.value,
        "rules": _rules_for(level),
    }


def data_classification_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 6,
        "levels": [c.value for c in DataClassification],
        "default_classification": DataClassification.INTERNAL.value,
        "rules_by_level": {c.value: _rules_for(c) for c in DataClassification},
        "auto_classification_signals": [
            "wallet_address",
            "sanctions_hit",
            "pii_detected",
            "case_fz115",
            "evidence_chain",
        ],
        "principle_ru": "Классификация данных определяет шифрование, логирование и правила экспорта",
    }


def can_export(role: str, classification: DataClassification | str) -> bool:
    if isinstance(classification, str):
        classification = DataClassification(classification)
    rules = _rules_for(classification)
    return role in rules["export"]["allowed_roles"]
