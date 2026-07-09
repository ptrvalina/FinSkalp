"""RFC-0017 Ch.7 — integrity verification."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def verify_integrity(
    *,
    content_hash: str,
    size_bytes: int,
    mime_type: str,
    payload: dict[str, Any] | None = None,
    expected_hash: str | None = None,
    entity_type: str | None = None,
    entity_value: str | None = None,
    source_type: str | None = None,
) -> dict[str, Any]:
    """
    Verify evidence integrity: hash, size, mime consistency.
    Returns verification result with ok flag and details.
    """
    errors: list[str] = []
    computed_hash: str | None = None

    if payload is not None:
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        actual_size = len(blob.encode("utf-8"))
        if actual_size != size_bytes:
            errors.append(f"size_mismatch: expected {size_bytes}, got {actual_size}")
        if entity_type and entity_value and source_type:
            from flowsint_crypto_compliance.platform.v2.evidence_center import content_hash_from_finding

            core_payload = {
                k: v
                for k, v in payload.items()
                if k not in ("collector_actor", "eccf_framework", "entity_type", "entity_value")
            }
            computed_hash = content_hash_from_finding(
                entity_type=entity_type,
                entity_value=entity_value,
                source_type=source_type,
                payload=core_payload,
            )
        else:
            computed_hash = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        if computed_hash != content_hash:
            errors.append("content_hash_mismatch")

    if expected_hash and expected_hash != content_hash:
        errors.append("expected_hash_mismatch")

    if not mime_type or len(mime_type) > 128:
        errors.append("invalid_mime_type")

    return {
        "ok": len(errors) == 0,
        "content_hash": content_hash,
        "computed_hash": computed_hash,
        "size_bytes": size_bytes,
        "mime_type": mime_type,
        "errors": errors,
    }
