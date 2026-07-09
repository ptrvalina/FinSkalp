"""RFC-0016 — read-only signal acquisition from platform subsystems."""

from __future__ import annotations

import re
import uuid
from typing import Any

_CHAIN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("tron", re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")),
    ("eth", re.compile(r"^0x[a-fA-F0-9]{40}$")),
    ("btc", re.compile(r"^(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$")),
]


def detect_chain_for_address(entity_key: str) -> str | None:
    key = entity_key.strip()
    for chain, pattern in _CHAIN_PATTERNS:
        if pattern.match(key):
            return chain
    return None


def _blockchain_signals(entity_key: str, chain: str | None) -> dict[str, Any]:
    chain_key = chain or detect_chain_for_address(entity_key)
    if not chain_key:
        return {}

    signals: dict[str, Any] = {"address": entity_key, "chain": chain_key, "_acquired_from": "blockchain_intelligence"}

    try:
        from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.service import (
            get_blockchain_intelligence_service,
        )

        svc = get_blockchain_intelligence_service()
        profile = svc.get_profile_signals(entity_key, chain=chain_key)
        signals.update(profile)
    except Exception:
        pass

    try:
        from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.sync_store import (
            get_block_sync_store,
        )

        transfers = get_block_sync_store().get_transfers_for_address(chain_key, entity_key)
        if transfers:
            signals.setdefault("transaction_count", len(transfers))
            signals.setdefault(
                "volume_usd",
                sum(float(t.get("amount") or 0) for t in transfers),
            )
            signals["_indexed_transfers"] = len(transfers)
    except Exception:
        pass

    return signals


def _registry_signals(entity_key: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.crif.compliance_checks import run_organization_checks
    from flowsint_crypto_compliance.platform.v2.crif.sanctions import screen_sanctions

    sanctions = screen_sanctions(entity_key)
    exact = [s for s in sanctions if s.get("match_type") == "exact"]
    probable = [s for s in sanctions if s.get("requires_analyst_confirmation")]

    stub_records = [
        {
            "entity_type": "Organization",
            "entity_value": entity_key,
            "payload": {"registration_number": "stub"} if len(entity_key) > 3 else {},
        }
    ]
    checks = run_organization_checks(stub_records, organization_key=entity_key)

    return {
        "organization": entity_key,
        "sanctioned": bool(exact),
        "sanction_matches": sanctions,
        "probable_matches_pending_analyst": len(probable),
        "license_status": "unknown",
        "org_status": "active" if checks and checks[0].get("passed") else "unknown",
        "compliance_checks": checks,
        "check_failures": sum(1 for c in checks if not c.get("passed")),
        "_acquired_from": "crif",
    }


def _osint_signals(entity_key: str, tenant_id: uuid.UUID) -> dict[str, Any]:
    mentions: list[dict[str, Any]] = []
    try:
        from flowsint_crypto_compliance.platform.v2.knowledge_store import get_knowledge_graph_store

        store = get_knowledge_graph_store()
        for ent in store.search_entities_by_value(tenant_id, entity_key):
            if ent.entity_type in ("osint_mention", "mention", "social_account", "domain"):
                mentions.append(
                    {
                        "source": ent.source_type or "kg",
                        "entity_type": ent.entity_type,
                        "title": ent.display_name,
                        "confidence": ent.confidence,
                    }
                )
    except Exception:
        pass

    return {
        "mentions": mentions,
        "source_count": len(mentions),
        "_acquired_from": "icf_kg",
    }


def _graph_signals(entity_key: str, tenant_id: uuid.UUID) -> dict[str, Any]:
    neighbors: list[dict[str, Any]] = []
    try:
        from flowsint_crypto_compliance.platform.v2.knowledge_store import get_knowledge_graph_store

        store = get_knowledge_graph_store()
        for ent in store.search_entities_by_value(tenant_id, entity_key)[:5]:
            neighbors.extend(store.get_neighbors(ent.id))
    except Exception:
        pass

    return {
        "neighbors": neighbors,
        "depth": 1,
        "neighbor_count": len(neighbors),
        "_acquired_from": "knowledge_graph",
    }


def _evidence_signals(case_ref: str | None) -> dict[str, Any]:
    if not case_ref:
        return {"items": [], "_acquired_from": "evidence_center"}

    try:
        from flowsint_crypto_compliance.platform.v2.gateway import list_case_evidence

        result = list_case_evidence(case_ref=case_ref)
        items = result.get("items") or result.get("evidence") or []
        if isinstance(items, dict):
            items = list(items.values())
        return {"items": items, "_acquired_from": "evidence_center", "case_ref": case_ref}
    except Exception:
        return {"items": [], "_acquired_from": "evidence_center"}


async def acquire_platform_signals(
    *,
    tenant_id: uuid.UUID,
    entity_key: str,
    case_ref: str | None,
    input_signals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Merge caller-provided signals with auto-acquired read-only subsystem payloads.
    Does NOT mutate KG, evidence, or source registries.
    """
    signals: dict[str, Any] = dict(input_signals or {})
    chain = None
    if isinstance(signals.get("blockchain_signals"), dict):
        chain = signals["blockchain_signals"].get("chain")

    if not signals.get("blockchain_signals"):
        bc = _blockchain_signals(entity_key, chain)
        if bc:
            signals["blockchain_signals"] = bc

    if not signals.get("registry_signals"):
        signals["registry_signals"] = _registry_signals(entity_key)

    if not signals.get("osint_signals"):
        signals["osint_signals"] = _osint_signals(entity_key, tenant_id)

    if not signals.get("graph_signals"):
        signals["graph_signals"] = _graph_signals(entity_key, tenant_id)

    if not signals.get("evidence_signals"):
        signals["evidence_signals"] = _evidence_signals(case_ref)

    signals["_signal_bridge"] = {
        "auto_acquired": [
            k
            for k in (
                "blockchain_signals",
                "registry_signals",
                "osint_signals",
                "graph_signals",
                "evidence_signals",
            )
            if k in signals and signals[k]
        ],
        "entity_key": entity_key,
        "case_ref": case_ref,
    }
    return signals
