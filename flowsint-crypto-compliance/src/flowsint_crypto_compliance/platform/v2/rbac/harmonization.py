"""RFC-0009 — Harmonized RBAC across compliance and investigation roles."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.services.compliance_rbac import (
    PERMISSIONS,
    ROLE_RANK,
    ComplianceRole,
    get_user_compliance_role,
    user_has_permission,
)

INVESTIGATION_ROLES = ("owner", "admin", "editor", "viewer")

INVESTIGATION_TO_COMPLIANCE: dict[str, ComplianceRole] = {
    "owner": ComplianceRole.ADMIN,
    "admin": ComplianceRole.ADMIN,
    "editor": ComplianceRole.SENIOR_ANALYST,
    "viewer": ComplianceRole.VIEWER,
}

PLATFORM_PERMISSIONS = {
    "investigation:read": {ComplianceRole.VIEWER, ComplianceRole.ANALYST, ComplianceRole.SENIOR_ANALYST, ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
    "investigation:edit": {ComplianceRole.ANALYST, ComplianceRole.SENIOR_ANALYST, ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
    "investigation:manage": {ComplianceRole.SENIOR_ANALYST, ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
    "workspace:comment": {ComplianceRole.ANALYST, ComplianceRole.SENIOR_ANALYST, ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
    "workspace:personalize": {ComplianceRole.VIEWER, ComplianceRole.ANALYST, ComplianceRole.SENIOR_ANALYST, ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
}


def _max_role(*roles: ComplianceRole) -> ComplianceRole:
    return max(roles, key=lambda r: ROLE_RANK[r])


def investigation_roles_to_compliance(roles: list[str] | None) -> ComplianceRole | None:
    if not roles:
        return None
    mapped = [INVESTIGATION_TO_COMPLIANCE[r] for r in roles if r in INVESTIGATION_TO_COMPLIANCE]
    return _max_role(*mapped) if mapped else None


def get_investigation_roles_for_user(db: Any, user_id: uuid.UUID, investigation_id: uuid.UUID | None) -> list[str]:
    if investigation_id is None:
        return []
    try:
        from flowsint_core.core.models import InvestigationUserRole
    except ImportError:  # pragma: no cover
        return []
    row = (
        db.query(InvestigationUserRole)
        .filter(
            InvestigationUserRole.user_id == user_id,
            InvestigationUserRole.investigation_id == investigation_id,
        )
        .first()
    )
    if not row or not row.roles:
        return []
    return [str(r.value if hasattr(r, "value") else r) for r in row.roles]


def effective_compliance_role(
    compliance_role: ComplianceRole,
    investigation_roles: list[str] | None,
) -> ComplianceRole:
    inv_equiv = investigation_roles_to_compliance(investigation_roles)
    if inv_equiv is None:
        return compliance_role
    return _max_role(compliance_role, inv_equiv)


def harmonized_user_has_permission(
    effective_role: ComplianceRole,
    permission: str,
) -> bool:
    if permission in PERMISSIONS:
        return user_has_permission(effective_role, permission)
    return effective_role in PLATFORM_PERMISSIONS.get(permission, set())


def resolve_effective_permissions(
    db: Any,
    user_id: uuid.UUID,
    *,
    investigation_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    compliance_role = get_user_compliance_role(db, user_id)
    investigation_roles = get_investigation_roles_for_user(db, user_id, investigation_id)
    effective = effective_compliance_role(compliance_role, investigation_roles)
    all_perms = sorted(
        p for p in {**PERMISSIONS, **PLATFORM_PERMISSIONS} if harmonized_user_has_permission(effective, p)
    )
    return {
        "user_id": str(user_id),
        "investigation_id": str(investigation_id) if investigation_id else None,
        "compliance_role": compliance_role.value,
        "investigation_roles": investigation_roles,
        "effective_role": effective.value,
        "permissions": all_perms,
    }


def harmonized_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0009",
        "schema_version": "9.0.0",
        "title": "RBAC Harmonization v2.0",
        "status": "complete",
        "planes": {
            "compliance": [r.value for r in ComplianceRole],
            "investigation": list(INVESTIGATION_ROLES),
        },
        "investigation_to_compliance": {k: v.value for k, v in INVESTIGATION_TO_COMPLIANCE.items()},
        "compliance_permissions": {k: sorted(r.value for r in v) for k, v in PERMISSIONS.items()},
        "platform_permissions": {k: sorted(r.value for r in v) for k, v in PLATFORM_PERMISSIONS.items()},
        "rule_ru": (
            "Эффективная роль = max(compliance_role, investigation_role→compliance). "
            "Права проверяются по единой матрице PERMISSIONS + platform permissions."
        ),
        "principle_ru": "Одна плоскость принятия решений для compliance API и investigation workspace.",
    }
