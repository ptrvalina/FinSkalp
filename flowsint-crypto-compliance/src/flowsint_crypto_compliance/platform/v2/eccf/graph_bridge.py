"""RFC-0017 Ch.12 — KG link bridge via ingest_pipeline (no direct graph mutation)."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.eccf.types import ECCFRecord
from flowsint_crypto_compliance.platform.v2.ingest_pipeline import get_ingest_pipeline


def link_evidence_to_entities(
    record: ECCFRecord,
    *,
    tenant_id: uuid.UUID,
    actor: str = "eccf.graph_bridge",
    relation_to: str | None = None,
    relation_type: str | None = None,
) -> dict[str, Any]:
    """
    Link evidence to KG entities via mandatory ingest_pipeline.
    No direct knowledge_graph mutation.
    """
    pipeline = get_ingest_pipeline()
    result = pipeline.ingest(
        tenant_id=tenant_id,
        source_type=record.source_type,
        entity_type=record.entity_type,
        entity_value=record.entity_value,
        case_ref=record.case_ref,
        actor=actor,
        confidence=float(record.payload.get("confidence") or 0.7),
        payload={
            **record.payload,
            "eccf_evidence_id": record.evidence_id,
            "content_hash": record.content_hash,
        },
        relation_to=relation_to,
        relation_type=relation_type,
        require_relation_evidence=bool(relation_to),
    )
    return {
        "ok": result.ok,
        "entity_id": str(result.entity_id) if result.entity_id else None,
        "evidence_id": str(result.evidence_id) if result.evidence_id else None,
        "relation_id": str(result.relation_id) if result.relation_id else None,
        "stages_completed": result.stages_completed,
        "errors": result.errors,
    }
