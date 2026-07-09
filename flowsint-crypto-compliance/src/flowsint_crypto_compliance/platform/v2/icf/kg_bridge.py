"""RFC-0014 Ch.1 — knowledge graph ingest bridge."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.ingest_pipeline import get_ingest_pipeline


def ingest_records(
    records: list[dict[str, Any]],
    *,
    tenant_id: uuid.UUID,
    case_ref: str | None = None,
    actor: str = "icf.kg_bridge",
) -> dict[str, Any]:
    """Explicit KG stage via mandatory ingest_pipeline — no bypass."""
    pipeline = get_ingest_pipeline()
    ingested = 0
    errors: list[str] = []
    entity_ids: list[str] = []

    for rec in records:
        et = str(rec.get("entity_type") or "unknown")
        val = str(rec.get("entity_value") or "")
        if not val:
            continue
        result = pipeline.ingest(
            tenant_id=tenant_id,
            source_type=str(rec.get("source_type") or "icf"),
            entity_type=et,
            entity_value=val,
            case_ref=case_ref,
            actor=actor,
            confidence=float(rec.get("confidence") or 0.5),
            payload=rec.get("payload") if isinstance(rec.get("payload"), dict) else rec,
            chain=rec.get("chain"),
            require_relation_evidence=False,
        )
        if result.ok:
            ingested += 1
            if result.entity_id:
                entity_ids.append(str(result.entity_id))
        else:
            errors.extend(result.errors)

    return {"ingested": ingested, "entity_ids": entity_ids, "errors": errors, "ok": ingested > 0 or not records}
