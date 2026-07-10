"""Tamper-evident hash chain for append-only ECCF audit entries (RFC-0017 Ch.10)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

_GENESIS = "0" * 64


def genesis_hash() -> str:
    """First link in the chain uses a fixed genesis sentinel."""
    return _GENESIS


def canonical_audit_blob(
    *,
    evidence_id: str,
    action: str,
    actor: str,
    timestamp: datetime,
    details: dict[str, Any],
    prev_hash: str,
) -> str:
    """Deterministic serialization for hash computation."""
    payload = {
        "evidence_id": evidence_id,
        "action": action,
        "actor": actor,
        "timestamp": timestamp.isoformat(),
        "details": details,
        "prev_hash": prev_hash,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def compute_entry_hash(
    *,
    evidence_id: str,
    action: str,
    actor: str,
    timestamp: datetime,
    details: dict[str, Any],
    prev_hash: str,
) -> str:
    """SHA-256 link hash binding this entry to the previous one."""
    blob = canonical_audit_blob(
        evidence_id=evidence_id,
        action=action,
        actor=actor,
        timestamp=timestamp,
        details=details,
        prev_hash=prev_hash,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def verify_chain(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify an ordered list of audit entries (each with prev_hash + entry_hash)."""
    errors: list[str] = []
    expected_prev = genesis_hash()
    for i, entry in enumerate(entries):
        prev = str(entry.get("prev_hash") or "")
        if prev != expected_prev:
            errors.append(f"link_{i}: prev_hash mismatch")
        recomputed = compute_entry_hash(
            evidence_id=str(entry.get("evidence_id") or ""),
            action=str(entry.get("action") or ""),
            actor=str(entry.get("actor") or ""),
            timestamp=entry["timestamp"]
            if isinstance(entry.get("timestamp"), datetime)
            else datetime.fromisoformat(str(entry.get("timestamp")).replace("Z", "+00:00")),
            details=entry.get("details") or {},
            prev_hash=prev,
        )
        stored = str(entry.get("entry_hash") or "")
        if stored != recomputed:
            errors.append(f"link_{i}: entry_hash mismatch")
        expected_prev = stored or recomputed
    return {"ok": len(errors) == 0, "errors": errors, "length": len(entries)}
