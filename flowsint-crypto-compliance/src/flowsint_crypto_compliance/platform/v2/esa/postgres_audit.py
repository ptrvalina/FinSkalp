"""ESA security audit Postgres persistence (Wave 5, behind feature flag)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def persist_security_audit_entry(entry: Any) -> None:
    """Append ESA audit entry to Postgres when flag is enabled."""
    try:
        from flowsint_crypto_compliance.feature_flags import esa_postgres_audit_enabled

        if not esa_postgres_audit_enabled():
            return
    except Exception:
        return

    try:
        from flowsint_core.core.postgre_db import SessionLocal

        from flowsint_crypto_compliance.storage.db_models import EsaSecurityAuditEntry

        session = SessionLocal()
        try:
            row = EsaSecurityAuditEntry(
                entry_id=entry.entry_id,
                event_type=entry.event_type.value if hasattr(entry.event_type, "value") else str(entry.event_type),
                actor=entry.actor,
                action=entry.action,
                resource=entry.resource or "",
                outcome=entry.outcome or "success",
                timestamp=entry.timestamp,
                details=dict(entry.details or {}),
            )
            session.add(row)
            session.commit()
        finally:
            session.close()
    except Exception as exc:
        logger.warning("esa postgres audit persist skipped: %s", exc)
