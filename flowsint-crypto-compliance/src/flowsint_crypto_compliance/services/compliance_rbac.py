"""RBAC for FinSkalp compliance module."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from flowsint_core.core.models import Profile
from flowsint_core.core.postgre_db import get_db
from flowsint_crypto_compliance.storage.db_models import ComplianceCase, ComplianceUserRole

# Re-use API auth when available (production); tests may import roles only.
try:
    from app.api.deps import get_current_user
except ImportError:  # pragma: no cover
    get_current_user = None  # type: ignore


class ComplianceRole(str, Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    SENIOR_ANALYST = "senior_analyst"
    COMPLIANCE_OFFICER = "compliance_officer"
    ADMIN = "admin"


ROLE_RANK = {
    ComplianceRole.VIEWER: 0,
    ComplianceRole.ANALYST: 1,
    ComplianceRole.SENIOR_ANALYST: 2,
    ComplianceRole.COMPLIANCE_OFFICER: 3,
    ComplianceRole.ADMIN: 4,
}

PERMISSIONS: dict[str, set[ComplianceRole]] = {
    "case:read": {
        ComplianceRole.VIEWER,
        ComplianceRole.ANALYST,
        ComplianceRole.SENIOR_ANALYST,
        ComplianceRole.COMPLIANCE_OFFICER,
        ComplianceRole.ADMIN,
    },
    "case:create": {ComplianceRole.ANALYST, ComplianceRole.SENIOR_ANALYST, ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
    "case:assign": {ComplianceRole.SENIOR_ANALYST, ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
    "case:transition": {ComplianceRole.ANALYST, ComplianceRole.SENIOR_ANALYST, ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
    "case:file_fz115": {ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
    "case:comment": {ComplianceRole.ANALYST, ComplianceRole.SENIOR_ANALYST, ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
    "batch:screen": {ComplianceRole.ANALYST, ComplianceRole.SENIOR_ANALYST, ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
    "webhook:manage": {ComplianceRole.ADMIN, ComplianceRole.COMPLIANCE_OFFICER},
    "watchlist:manage": {ComplianceRole.SENIOR_ANALYST, ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
    "audit:read": {ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.ADMIN},
}


def get_user_compliance_role(db: Session, user_id: uuid.UUID) -> ComplianceRole:
    row = db.query(ComplianceUserRole).filter(ComplianceUserRole.user_id == user_id).first()
    if row:
        try:
            return ComplianceRole(row.role)
        except ValueError:
            pass
    return ComplianceRole.ANALYST


def user_has_permission(role: ComplianceRole, permission: str) -> bool:
    return role in PERMISSIONS.get(permission, set())


def can_access_case(user: Profile, case: ComplianceCase, role: ComplianceRole) -> bool:
    if role == ComplianceRole.ADMIN:
        return True
    if case.owner_id == user.id:
        return True
    if case.assignee_id == user.id:
        return True
    return role in (ComplianceRole.COMPLIANCE_OFFICER, ComplianceRole.SENIOR_ANALYST)


def require_permission(permission: str) -> Callable:
    if get_current_user is None:
        raise RuntimeError("get_current_user not available")

    def _dep(
        current_user: Profile = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Profile:
        role = get_user_compliance_role(db, current_user.id)
        if not user_has_permission(role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission}")
        return current_user

    return _dep
