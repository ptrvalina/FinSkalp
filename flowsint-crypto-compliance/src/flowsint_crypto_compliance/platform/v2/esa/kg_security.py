"""RFC-0020 Ch.11 — knowledge graph security policies."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.esa.data_classification import can_export
from flowsint_crypto_compliance.platform.v2.esa.types import DataClassification, EnterpriseRole


def kg_security_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 11,
        "entity_access": {
            "Wallet": {"min_role": "analyst", "classification": "internal"},
            "Case": {"min_role": "analyst", "classification": "confidential"},
            "Person": {"min_role": "senior_analyst", "classification": "confidential"},
            "Organization": {"min_role": "analyst", "classification": "internal"},
            "Transaction": {"min_role": "analyst", "classification": "internal"},
            "Evidence": {"min_role": "analyst", "classification": "confidential"},
            "SanctionHit": {"min_role": "senior_analyst", "classification": "restricted"},
        },
        "relation_access": {
            "OWNS": {"min_role": "analyst"},
            "TRANSACTED_WITH": {"min_role": "analyst"},
            "LINKED_TO": {"min_role": "senior_analyst"},
            "SANCTIONED_BY": {"min_role": "senior_analyst"},
            "EVIDENCE_OF": {"min_role": "analyst"},
        },
        "export_controls": {
            "graph_snapshot": {
                "allowed_roles": ["lead", "admin", "auditor"],
                "max_nodes": 10_000,
                "watermark": True,
                "audit_event": "export",
            },
            "entity_neighbors": {
                "allowed_roles": ["analyst", "senior_analyst", "lead", "admin"],
                "depth_max": 3,
            },
            "full_graph_dump": {
                "allowed_roles": ["admin"],
                "approval_required": True,
            },
        },
        "mutation_policy": {
            "direct_mutation_forbidden": True,
            "allowed_path": "ingest_pipeline → knowledge_store → graph_projection",
            "forbidden_modules": ["knowledge_graph direct write"],
        },
        "principle_ru": "Доступ к сущностям и связям KG по роли и классификации — экспорт только с аудитом",
    }


def can_access_entity(role: str, entity_type: str) -> bool:
    manifest = kg_security_manifest()
    policy = manifest["entity_access"].get(entity_type)
    if not policy:
        return role in ("admin", "lead")
    min_role = policy["min_role"]
    role_rank = {r.value: i for i, r in enumerate(EnterpriseRole)}
    return role_rank.get(role, 0) >= role_rank.get(min_role, 0)


def can_export_graph(role: str, export_type: str, classification: str = "internal") -> bool:
    manifest = kg_security_manifest()
    controls = manifest["export_controls"].get(export_type, {})
    allowed = controls.get("allowed_roles", [])
    if role not in allowed:
        return False
    return can_export(role, DataClassification(classification))
