"""RFC-0017 Ch.5 — evidence generator from collector payload."""

from __future__ import annotations

import json
import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.eccf.id_generator import allocate_evidence_id
from flowsint_crypto_compliance.platform.v2.eccf.types import ECCFRecord, EvidenceCategory, EvidenceLifecycle
from flowsint_crypto_compliance.platform.v2.evidence_center import content_hash_from_finding


def _infer_category(source_type: str, entity_type: str) -> EvidenceCategory:
    st = source_type.lower()
    et = entity_type.lower()
    if "blockchain" in st or et in ("blockchain_address", "wallet", "transaction"):
        return EvidenceCategory.BLOCKCHAIN
    if "registry" in st or et in ("registry_record", "sanction_record", "company"):
        return EvidenceCategory.REGISTRY
    if et in ("document", "pdf", "image", "ocr_doc", "contract"):
        return EvidenceCategory.DOCUMENT
    if "user" in st or et == "user_uploaded":
        return EvidenceCategory.USER
    return EvidenceCategory.OSINT


def _payload_size(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def _infer_mime(payload: dict[str, Any], source_type: str) -> str:
    if payload.get("mime_type"):
        return str(payload["mime_type"])
    if payload.get("content_type"):
        return str(payload["content_type"])
    if "document" in source_type.lower():
        return "application/json"
    return "application/json"


def generate_evidence(
    *,
    tenant_id: uuid.UUID,
    collector_payload: dict[str, Any],
    case_ref: str | None = None,
    actor: str = "eccf.generator",
) -> ECCFRecord:
    """Generate ECCF record from collector payload — no persistence."""
    entity_type = str(collector_payload.get("entity_type") or "unknown")
    entity_value = str(collector_payload.get("entity_value") or "")
    source_type = str(collector_payload.get("source_type") or "osint")
    payload = collector_payload.get("payload") if isinstance(collector_payload.get("payload"), dict) else collector_payload
    if not isinstance(payload, dict):
        payload = {"raw": payload}

    full_payload = {
        **payload,
        "entity_type": entity_type,
        "entity_value": entity_value,
        "collector_actor": actor,
        "eccf_framework": "RFC-0017",
    }

    content_hash = content_hash_from_finding(
        entity_type=entity_type,
        entity_value=entity_value,
        source_type=source_type,
        payload=payload,
    )
    category = _infer_category(source_type, entity_type)
    size_bytes = int(collector_payload.get("size_bytes") or _payload_size(full_payload))
    mime_type = _infer_mime(payload, source_type)

    return ECCFRecord(
        evidence_id=allocate_evidence_id(),
        tenant_id=str(tenant_id),
        category=category,
        version=1,
        content_hash=content_hash,
        size_bytes=size_bytes,
        mime_type=mime_type,
        lifecycle=EvidenceLifecycle.DRAFT,
        source_type=source_type,
        entity_type=entity_type,
        entity_value=entity_value,
        case_ref=case_ref,
        payload=full_payload,
    )
