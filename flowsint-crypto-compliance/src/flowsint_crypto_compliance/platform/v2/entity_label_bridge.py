"""Bridge EntityLabel upserts into canonical Knowledge Graph (RFC-0002 M2, TD-S1)."""

from __future__ import annotations

import os
import uuid
from typing import Any

from flowsint_crypto_compliance.attribution.types import EntityLabel


def _default_tenant_id() -> uuid.UUID:
    return uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))


def sync_entity_label_to_kg(
    label: EntityLabel,
    *,
    actor: str = "entity_label_bridge",
    tenant_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Project accepted EntityLabel into canonical Entity + Evidence via IngestPipeline."""
    from flowsint_crypto_compliance.platform.v2.ingest_pipeline import get_ingest_pipeline

    tenant = tenant_id or _default_tenant_id()
    pipeline = get_ingest_pipeline()
    result = pipeline.ingest(
        tenant_id=tenant,
        source_type=label.source,
        entity_type="crypto_address",
        entity_value=f"{label.chain}:{label.address}",
        payload={
            "label": label.label,
            "category": label.category,
            "risk_score": label.risk_score,
            "sanctioned": label.sanctioned,
            "cluster_ref": label.cluster_ref,
            "evidence": label.evidence,
            "tier": label.tier,
        },
        actor=actor,
        chain=label.chain,
        display_name=label.label,
        confidence=float(label.confidence),
        require_relation_evidence=False,
    )
    return {
        "synced": result.ok,
        "entity_id": str(result.entity_id) if result.entity_id else None,
        "evidence_id": str(result.evidence_id) if result.evidence_id else None,
        "merge_decision": result.merge_decision,
        "errors": result.errors,
    }
