"""RFC-0020 Ch.5 — RBAC + ABAC authorization engine."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.esa.authentication import admin_requires_mfa
from flowsint_crypto_compliance.platform.v2.esa.types import (
    ABACAttribute,
    AccessDecision,
    DataClassification,
    EnterpriseRole,
    SecurityResource,
    SecurityUser,
)
from flowsint_crypto_compliance.platform.v2.rbac.harmonization import (
    harmonized_manifest,
    resolve_effective_permissions,
)

# Enterprise role → RBAC permission sets (extends RFC-0009)
_ROLE_PERMISSIONS: dict[EnterpriseRole, set[str]] = {
    EnterpriseRole.ANALYST: {
        "case:read", "case:comment", "case:transition", "batch:screen",
        "investigation:read", "investigation:edit", "workspace:comment",
        "eccf:view", "eccf:use", "eccf:comment",
    },
    EnterpriseRole.SENIOR_ANALYST: {
        "case:read", "case:create", "case:comment", "case:transition", "case:assign",
        "batch:screen", "investigation:read", "investigation:edit", "investigation:manage",
        "workspace:comment", "workspace:personalize",
        "eccf:view", "eccf:use", "eccf:comment", "eccf:export",
    },
    EnterpriseRole.LEAD: {
        "case:read", "case:create", "case:comment", "case:transition", "case:assign",
        "batch:screen", "watchlist:manage", "audit:read",
        "investigation:read", "investigation:edit", "investigation:manage",
        "workspace:comment", "workspace:personalize",
        "eccf:view", "eccf:use", "eccf:comment", "eccf:export", "eccf:archive",
    },
    EnterpriseRole.ADMIN: {
        "case:read", "case:create", "case:comment", "case:transition", "case:assign",
        "case:file_fz115", "batch:screen", "webhook:manage", "watchlist:manage", "audit:read",
        "investigation:read", "investigation:edit", "investigation:manage",
        "workspace:comment", "workspace:personalize",
        "eccf:view", "eccf:use", "eccf:comment", "eccf:export", "eccf:archive", "eccf:register",
    },
    EnterpriseRole.AUDITOR: {
        "case:read", "audit:read", "investigation:read", "workspace:personalize",
        "eccf:view", "eccf:export",
    },
    EnterpriseRole.INTEGRATION_SERVICE: {
        "batch:screen", "eccf:register", "investigation:read",
    },
}

# Minimum role clearance for data classification
_CLASSIFICATION_CLEARANCE: dict[DataClassification, set[EnterpriseRole]] = {
    DataClassification.PUBLIC: set(EnterpriseRole),
    DataClassification.INTERNAL: {
        EnterpriseRole.ANALYST, EnterpriseRole.SENIOR_ANALYST, EnterpriseRole.LEAD,
        EnterpriseRole.ADMIN, EnterpriseRole.AUDITOR, EnterpriseRole.INTEGRATION_SERVICE,
    },
    DataClassification.CONFIDENTIAL: {
        EnterpriseRole.SENIOR_ANALYST, EnterpriseRole.LEAD, EnterpriseRole.ADMIN, EnterpriseRole.AUDITOR,
    },
    DataClassification.RESTRICTED: {EnterpriseRole.LEAD, EnterpriseRole.ADMIN},
}

_ACTION_PERMISSION_MAP: dict[str, str] = {
    "read": "case:read",
    "write": "case:transition",
    "export": "eccf:export",
    "admin": "audit:read",
    "register": "eccf:register",
    "manage": "investigation:manage",
}


def _resolve_db_permissions(
    db: Any,
    user_id: str,
    *,
    investigation_id: uuid.UUID | None = None,
) -> list[str]:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return []
    result = resolve_effective_permissions(db, uid, investigation_id=investigation_id)
    return list(result.get("permissions", []))


def _evaluate_abac(
    user: SecurityUser,
    resource: SecurityResource,
    action: str,
    attributes: dict[str, Any] | None,
) -> tuple[bool, str]:
    attrs = dict(attributes or {})
    attrs.update(user.attributes)
    attrs.update(resource.attributes)

    # Tenant isolation
    user_tenant = user.tenant_id or attrs.get(ABACAttribute.TENANT_ID.value, "")
    resource_tenant = resource.tenant_id or attrs.get(ABACAttribute.TENANT_ID.value, "")
    if user_tenant and resource_tenant and user_tenant != resource_tenant:
        return False, "tenant_mismatch"

    # Data classification clearance
    clearance = _CLASSIFICATION_CLEARANCE.get(resource.data_classification, set())
    if user.role not in clearance:
        return False, f"insufficient_clearance_for_{resource.data_classification.value}"

    # Case scope — analysts limited to assigned cases unless lead/admin
    case_ref = attrs.get(ABACAttribute.CASE_REF.value) or resource.attributes.get("case_ref")
    user_cases = attrs.get("assigned_cases", [])
    if (
        case_ref
        and user_cases
        and user.role in (EnterpriseRole.ANALYST, EnterpriseRole.SENIOR_ANALYST)
        and case_ref not in user_cases
    ):
        return False, "case_not_assigned"

    # Export restricted data requires explicit export action + lead+
    if action == "export" and resource.data_classification == DataClassification.RESTRICTED:
        if user.role not in (EnterpriseRole.LEAD, EnterpriseRole.ADMIN, EnterpriseRole.AUDITOR):
            return False, "restricted_export_denied"

    # Service accounts cannot access admin actions
    if user.service_account and action == "admin":
        return False, "service_account_admin_denied"

    return True, "abac_ok"


def evaluate_access(
    user: SecurityUser | dict[str, Any],
    resource: SecurityResource | dict[str, Any],
    action: str,
    attributes: dict[str, Any] | None = None,
    *,
    db: Any = None,
) -> AccessDecision:
    """Evaluate RBAC + ABAC access decision."""
    if isinstance(user, dict):
        role_raw = user.get("role", EnterpriseRole.ANALYST.value)
        user = SecurityUser(
            user_id=str(user.get("user_id", "anonymous")),
            role=EnterpriseRole(str(role_raw)),
            tenant_id=str(user.get("tenant_id", "")),
            mfa_verified=bool(user.get("mfa_verified", False)),
            service_account=bool(user.get("service_account", False)),
            attributes=dict(user.get("attributes", {})),
        )
    if isinstance(resource, dict):
        cls_raw = resource.get("data_classification", DataClassification.INTERNAL.value)
        resource = SecurityResource(
            resource_type=str(resource.get("resource_type", "unknown")),
            resource_id=str(resource.get("resource_id", "")),
            data_classification=DataClassification(str(cls_raw)),
            tenant_id=str(resource.get("tenant_id", "")),
            attributes=dict(resource.get("attributes", {})),
        )

    permission = _ACTION_PERMISSION_MAP.get(action, f"{resource.resource_type}:{action}")
    role_perms = _ROLE_PERMISSIONS.get(user.role, set())
    rbac_ok = permission in role_perms

    effective_perms: list[str] = sorted(role_perms)
    if db is not None:
        inv_raw = (attributes or {}).get(ABACAttribute.INVESTIGATION_ID.value)
        inv_id = None
        if inv_raw:
            try:
                inv_id = uuid.UUID(str(inv_raw))
            except ValueError:
                pass
        db_perms = _resolve_db_permissions(db, user.user_id, investigation_id=inv_id)
        if db_perms:
            effective_perms = db_perms
            rbac_ok = permission in db_perms

    if not admin_requires_mfa(user.role.value, mfa_verified=user.mfa_verified):
        return AccessDecision(
            allowed=False,
            reason="mfa_required_for_admin",
            rbac_ok=False,
            abac_ok=False,
            permission=permission,
            effective_permissions=effective_perms,
        )

    abac_ok, abac_reason = _evaluate_abac(user, resource, action, attributes)

    allowed = rbac_ok and abac_ok
    reason = "allowed" if allowed else (
        "rbac_denied" if not rbac_ok else abac_reason
    )

    return AccessDecision(
        allowed=allowed,
        reason=reason,
        rbac_ok=rbac_ok,
        abac_ok=abac_ok,
        permission=permission,
        effective_permissions=effective_perms,
    )


def authorization_manifest() -> dict[str, Any]:
    rbac = harmonized_manifest()
    return {
        "rfc": "RFC-0020",
        "chapter": 5,
        "model": "RBAC+ABAC",
        "enterprise_roles": [r.value for r in EnterpriseRole],
        "role_permissions": {k.value: sorted(v) for k, v in _ROLE_PERMISSIONS.items()},
        "classification_clearance": {
            k.value: sorted(r.value for r in v) for k, v in _CLASSIFICATION_CLEARANCE.items()
        },
        "abac_attributes": [a.value for a in ABACAttribute],
        "harmonized_rbac": rbac,
        "principle_ru": "RBAC через RFC-0009 + ABAC по tenant, классификации и scope дела",
    }
