"""FastAPI dependencies for harmonized RBAC (RFC-0009)."""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from flowsint_core.core.models import Profile
from flowsint_core.core.postgre_db import get_db
from flowsint_crypto_compliance.platform.v2.rbac.harmonization import (
    effective_compliance_role,
    get_investigation_roles_for_user,
    harmonized_user_has_permission,
)
from flowsint_crypto_compliance.services.compliance_rbac import get_user_compliance_role

try:
    from app.api.deps import get_current_user
except ImportError:  # pragma: no cover
    get_current_user = None  # type: ignore


def require_harmonized_permission(permission: str) -> Callable:
    if get_current_user is None:
        raise RuntimeError("get_current_user not available")

    def _dep(
        current_user: Profile = Depends(get_current_user),
        db: Session = Depends(get_db),
        investigation_id: uuid.UUID | None = Query(None),
    ) -> Profile:
        compliance_role = get_user_compliance_role(db, current_user.id)
        inv_roles = get_investigation_roles_for_user(db, current_user.id, investigation_id)
        effective = effective_compliance_role(compliance_role, inv_roles)
        if not harmonized_user_has_permission(effective, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing harmonized permission: {permission}",
            )
        return current_user

    return _dep
