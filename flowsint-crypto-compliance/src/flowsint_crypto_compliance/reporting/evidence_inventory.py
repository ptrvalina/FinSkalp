"""SHA-256 evidence inventory for forensic reports."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return sha256_bytes(payload.encode("utf-8"))


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def build_evidence_inventory(
    *,
    case_ref: str,
    sources: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build exhibit table with reproducible SHA-256 hashes."""
    exhibits: list[dict[str, Any]] = []
    seq = 1
    for key, payload in sources.items():
        if payload is None:
            continue
        if isinstance(payload, bytes):
            digest = sha256_bytes(payload)
            size = len(payload)
        elif isinstance(payload, str):
            digest = sha256_text(payload)
            size = len(payload.encode("utf-8"))
        else:
            digest = sha256_json(payload)
            size = len(json.dumps(payload, default=str))
        exhibits.append(
            {
                "exhibit_id": f"E-{seq}",
                "source_key": key,
                "description": _describe(key),
                "sha256": digest,
                "size_bytes": size,
                "tier": _tier_for(key),
            }
        )
        seq += 1
    return exhibits


def verify_exhibit_hash(payload: Any, expected_sha256: str) -> bool:
    if isinstance(payload, bytes):
        return sha256_bytes(payload) == expected_sha256
    if isinstance(payload, str):
        return sha256_text(payload) == expected_sha256
    return sha256_json(payload) == expected_sha256


def _describe(key: str) -> str:
    mapping = {
        "trongrid_account": "TronGrid account state response",
        "trongrid_transfers": "TronGrid TRC20 transfer history",
        "onchain_verification": "On-chain verification record (ledger replay)",
        "attribution_snapshot": "FinSkalp attribution engine snapshot",
        "fusion_graph": "Fusion graph export",
        "sanctions_check": "Sanctions/watchlist screening response",
    }
    return mapping.get(key, key.replace("_", " ").title())


def _tier_for(key: str) -> str:
    if key in {"trongrid_transfers", "trongrid_account", "onchain_verification"}:
        return "Tier-1 ledger-confirmed"
    if key in {"sanctions_check", "attribution_snapshot"}:
        return "Tier-1/Tier-2 mixed"
    return "Tier-2 single-source"
