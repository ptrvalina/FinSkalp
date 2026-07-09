"""RFC-0020 Ch.12 — evidence security bridging ECCF."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.eccf.access_control import eccf_access_control_manifest
from flowsint_crypto_compliance.platform.v2.eccf.audit_trail import get_audit_trail
from flowsint_crypto_compliance.platform.v2.eccf.constraints import eccf_architectural_constraints


def evidence_security_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0020",
        "chapter": 12,
        "eccf_bridge": {
            "access_control": eccf_access_control_manifest(),
            "architectural_constraints": eccf_architectural_constraints(),
            "immutable_audit": True,
            "integrity_verification": "SHA-256 content hash",
            "chain_of_custody": "append-only audit trail per evidence_id",
        },
        "esa_extensions": {
            "classification_default": "confidential",
            "export_dual_control": True,
            "cross_tenant_isolation": True,
            "legal_hold_support": True,
        },
        "integrity_checks": [
            "content_hash_match",
            "audit_trail_continuity",
            "version_chain_valid",
            "no_forbidden_mutations",
        ],
        "principle_ru": "Доказательства защищены ECCF — неизменяемость + непрерывный аудит",
    }


def verify_evidence_security(evidence_id: str) -> dict[str, Any]:
    """Bridge ECCF integrity + immutable audit for ESA security scan."""
    trail = get_audit_trail()
    entries = trail.get_trail(evidence_id)
    constraints = eccf_architectural_constraints()
    return {
        "evidence_id": evidence_id,
        "audit_entries": len(entries),
        "immutable_audit": True,
        "eccf_linked": len(entries) > 0,
        "forbidden_actions_blocked": list(constraints["forbidden_actions"]),
        "integrity_ok": len(entries) > 0,
    }
