"""RFC-0017 Ch.8 — evidence versioning (immutable prior versions)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.eccf.generator import generate_evidence
from flowsint_crypto_compliance.platform.v2.eccf.id_generator import allocate_evidence_id
from flowsint_crypto_compliance.platform.v2.eccf.repository import get_eccf_repository
from flowsint_crypto_compliance.platform.v2.eccf.types import ECCFRecord, EvidenceLifecycle
import uuid


def diff_metadata(old: ECCFRecord, new: ECCFRecord) -> dict[str, Any]:
    """Diff metadata between two evidence versions (content excluded)."""
    old_d = old.to_dict()
    new_d = new.to_dict()
    skip = {"payload", "content_hash", "created_at", "updated_at"}
    changes: dict[str, dict[str, Any]] = {}
    for key in new_d:
        if key in skip:
            continue
        if old_d.get(key) != new_d.get(key):
            changes[key] = {"from": old_d.get(key), "to": new_d.get(key)}
    return {"from_version": old.version, "to_version": new.version, "changes": changes}


def create_new_version(
    evidence_id: str,
    *,
    collector_payload: dict[str, Any] | None = None,
    actor: str = "eccf.versioning",
) -> tuple[ECCFRecord, dict[str, Any]]:
    """
    Create new evidence version. Prior version becomes immutable (already is).
    Returns (new_record, metadata_diff).
    """
    repo = get_eccf_repository()
    prior = repo.get(evidence_id)
    if prior is None:
        raise KeyError(evidence_id)

    prior.immutable = True
    prior.updated_at = datetime.now(timezone.utc)

    if collector_payload:
        new_rec = generate_evidence(
            tenant_id=uuid.UUID(prior.tenant_id),
            collector_payload=collector_payload,
            case_ref=prior.case_ref,
            actor=actor,
        )
    else:
        new_rec = ECCFRecord(
            evidence_id=allocate_evidence_id(),
            tenant_id=prior.tenant_id,
            category=prior.category,
            version=prior.version + 1,
            content_hash=prior.content_hash,
            size_bytes=prior.size_bytes,
            mime_type=prior.mime_type,
            lifecycle=EvidenceLifecycle.DRAFT,
            source_type=prior.source_type,
            entity_type=prior.entity_type,
            entity_value=prior.entity_value,
            case_ref=prior.case_ref,
            payload=dict(prior.payload),
            provenance=dict(prior.provenance),
        )

    new_rec.version = prior.version + 1
    new_rec.prior_version_id = prior.evidence_id
    new_rec.provenance["prior_version"] = prior.evidence_id
    new_rec.provenance["versioned_by"] = actor

    stored, _ = repo.store(new_rec, bridge_kg=False)
    meta_diff = diff_metadata(prior, stored)
    return stored, meta_diff
