"""RFC-0017 Ch.18 — architectural constraints and forbidden actions."""

from __future__ import annotations

from typing import Any


_FORBIDDEN_ACTIONS = frozenset({
    "delete_evidence",
    "modify_content",
    "bypass_audit_trail",
    "direct_graph_mutation",
    "bypass_integrity_check",
    "overwrite_content_hash",
    "silent_version_replace",
})


def eccf_architectural_constraints() -> dict[str, Any]:
    return {
        "forbidden_actions": sorted(_FORBIDDEN_ACTIONS),
        "forbidden_modules": [
            "flowsint_crypto_compliance.platform.v2.knowledge_graph",
        ],
        "principle": "Evidence content is immutable — append-only audit trail",
        "principle_ru": "Содержимое доказательств неизменяемо — только дополняемый аудит",
        "immutable_fields": [
            "content_hash",
            "payload",
            "size_bytes",
            "mime_type",
        ],
        "allowed_mutations": [
            "lifecycle",
            "archived",
            "kg_evidence_id",
            "provenance",
        ],
    }


def assert_not_forbidden(action: str) -> None:
    if action in _FORBIDDEN_ACTIONS:
        raise PermissionError(f"ECCF forbidden action: {action}")
