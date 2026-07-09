"""Canonical Platform v2 API gateway — RFC-0002 M3/M4, RFC-0003 Knowledge Graph."""

from __future__ import annotations

from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router
from app.api.deps import get_current_user
from flowsint_core.core.postgre_db import get_db
from flowsint_crypto_compliance.platform.v2.rbac.deps import require_harmonized_permission

router = create_platform_v2_router(
    get_current_user=get_current_user,
    require_case_read=require_harmonized_permission("case:read"),
    require_batch_screen=require_harmonized_permission("batch:screen"),
    require_case_create=require_harmonized_permission("case:create"),
    get_db=get_db,
)
