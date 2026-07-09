"""RFC-0017 Ch.9 — provenance chain."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.eccf.types import ECCFRecord


def build_provenance(
    record: ECCFRecord,
    *,
    collector_id: str | None = None,
    source_uri: str | None = None,
    actor: str = "eccf.pipeline",
    acquisition_method: str | None = None,
    parent_evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Build provenance metadata answering Ch.9 questions:
    who, when, how, from where, derived from what.
    """
    provenance: dict[str, Any] = {
        "who": actor,
        "when": datetime.now(timezone.utc).isoformat(),
        "how": acquisition_method or record.source_type,
        "from_where": source_uri or record.payload.get("original_uri") or record.source_type,
        "derived_from": parent_evidence_ids or [],
        "collector_id": collector_id,
        "category": record.category.value,
        "entity_type": record.entity_type,
        "entity_value": record.entity_value,
        "case_ref": record.case_ref,
        "content_hash": record.content_hash,
        "version": record.version,
        "chain_of_custody": "ECCF-v2.0",
    }
    if record.prior_version_id:
        provenance["prior_version_id"] = record.prior_version_id
    return provenance
