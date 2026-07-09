"""Evidence Center — dual-write OsintFinding → finskalp_evidence (RFC-0002 M1)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import Evidence, TrustLevel


def content_hash_from_finding(
    *,
    entity_type: str,
    entity_value: str,
    source_type: str,
    payload: dict[str, Any] | None = None,
) -> str:
    """Deterministic hash for deduplication in Evidence Center."""
    blob = json.dumps(
        {
            "entity_type": entity_type,
            "entity_value": entity_value,
            "source_type": source_type,
            "payload": payload or {},
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def osint_finding_to_evidence(row: dict[str, Any]) -> Evidence:
    """Map legacy OsintFinding row to canonical Evidence."""
    tenant_id = uuid.UUID(str(row["tenant_id"]))
    case_id = uuid.UUID(str(row["case_id"])) if row.get("case_id") else None
    payload = row.get("payload") or {}
    if isinstance(payload, str):
        payload = json.loads(payload) if payload else {}
    et = str(row.get("entity_type") or "unknown")
    ev = str(row.get("entity_value") or "")
    source_type = str(row.get("source_type") or "osint")
    content_hash = content_hash_from_finding(
        entity_type=et,
        entity_value=ev,
        source_type=source_type,
        payload=payload,
    )
    confidence = float(row.get("confidence") or 0.5)
    discovered_raw = row.get("discovered_at")
    if isinstance(discovered_raw, datetime):
        discovered_at = discovered_raw
    elif discovered_raw:
        discovered_at = datetime.fromisoformat(str(discovered_raw).replace("Z", "+00:00"))
    else:
        discovered_at = datetime.now(timezone.utc)
    return Evidence(
        id=uuid.UUID(str(row["id"])) if row.get("id") else uuid.uuid4(),
        tenant_id=tenant_id,
        case_id=case_id,
        source_type=source_type,
        content_hash=content_hash,
        discovered_at=discovered_at,
        trust=TrustLevel(
            source_reliability=min(1.0, confidence + 0.05),
            information_credibility=confidence,
            sample_size=1,
        ),
        payload={
            **payload,
            "entity_type": et,
            "entity_value": ev,
            "case_ref": row.get("case_ref"),
            "legacy_table": "osint_findings",
        },
    )


def dual_write_osint_finding(row: dict[str, Any], *, session: Any | None = None) -> uuid.UUID | None:
    """Dual-write: persist OsintFinding row into finskalp_evidence."""
    evidence = osint_finding_to_evidence(row)
    own_session = session is None
    if own_session:
        try:
            from flowsint_core.core.postgre_db import SessionLocal

            session = SessionLocal()
        except Exception:
            return None
    try:
        from flowsint_crypto_compliance.storage.db_models import FinskalpEvidence

        existing = (
            session.query(FinskalpEvidence)
            .filter(
                FinskalpEvidence.tenant_id == evidence.tenant_id,
                FinskalpEvidence.content_hash == evidence.content_hash,
                FinskalpEvidence.case_id == evidence.case_id,
            )
            .first()
        )
        if existing:
            return existing.id
        row_db = FinskalpEvidence(
            id=evidence.id,
            tenant_id=evidence.tenant_id,
            case_id=evidence.case_id,
            entity_id=evidence.entity_id,
            source_type=evidence.source_type,
            content_hash=evidence.content_hash,
            snapshot_uri=evidence.snapshot_uri,
            trust_level=evidence.trust_level,
            payload=evidence.payload,
            discovered_at=evidence.discovered_at,
        )
        session.add(row_db)
        if own_session:
            session.commit()
        return evidence.id
    except Exception:
        if own_session and session is not None:
            try:
                session.rollback()
            except Exception:
                pass
        return None
    finally:
        if own_session and session is not None:
            try:
                session.close()
            except Exception:
                pass
