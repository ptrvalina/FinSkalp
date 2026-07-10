"""RFC-0016 — normalize incoming signals from subsystems."""

from __future__ import annotations

from typing import Any


def normalize_signals(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Normalize heterogeneous subsystem payloads into factor-group signal dicts.
    Read-only transformation — no mutation of source data.
    """
    normalized: dict[str, dict[str, Any]] = {}

    blockchain = raw.get("blockchain_signals") or raw.get("blockchain") or {}
    if blockchain:
        normalized["blockchain"] = {
            "transaction_count": blockchain.get("transaction_count")
            if blockchain.get("transaction_count") is not None
            else (blockchain.get("tx_count") if blockchain.get("tx_count") is not None else 0),
            "volume_usd": blockchain.get("volume_usd")
            if blockchain.get("volume_usd") is not None
            else (blockchain.get("total_volume") if blockchain.get("total_volume") is not None else 0.0),
            "risk_flags": blockchain.get("risk_flags") or blockchain.get("flags") or [],
            "mixer_exposure": blockchain.get("mixer_exposure") or blockchain.get("has_mixer"),
            "high_risk_counterparty": blockchain.get("high_risk_counterparty"),
            "chain": blockchain.get("chain"),
            "address": blockchain.get("address"),
            "_source": "blockchain_intelligence",
        }

    registry = raw.get("registry_signals") or raw.get("registry") or raw.get("crif") or {}
    if registry:
        normalized["registry"] = {
            "sanctioned": registry.get("sanctioned"),
            "license_status": registry.get("license_status"),
            "org_status": registry.get("org_status") or registry.get("status"),
            "check_failures": registry.get("check_failures") or registry.get("failed_checks"),
            "compliance_checks": registry.get("compliance_checks") or [],
            "organization": registry.get("organization") or registry.get("entity_value"),
            "_source": "crif",
        }

    osint = raw.get("osint_signals") or raw.get("osint") or raw.get("icf") or {}
    if osint:
        mentions = osint.get("mentions") or osint.get("items") or osint.get("records") or []
        normalized["osint"] = {
            "mentions": mentions,
            "negative_mentions": osint.get("negative_mentions") or sum(
                1 for m in mentions if (m.get("sentiment") or 0) < 0.3
            ),
            "avg_sentiment": osint.get("avg_sentiment") or _avg_sentiment(mentions),
            "source_count": osint.get("source_count") or len({m.get("source") for m in mentions if m.get("source")}),
            "_source": "icf",
        }

    graph = raw.get("graph_signals") or raw.get("graph") or raw.get("kg") or {}
    if graph:
        neighbors = graph.get("neighbors") or graph.get("relations") or []
        normalized["graph"] = {
            "neighbors": neighbors,
            "high_risk_links": graph.get("high_risk_links") or sum(
                1 for n in neighbors if (n.get("confidence") or 0) < 0.4 or n.get("relation_type") in ("SANCTIONED", "MIXER")
            ),
            "depth": graph.get("depth") or 1,
            "_source": "knowledge_store",
        }

    evidence = raw.get("evidence_signals") or raw.get("evidence") or {}
    if evidence:
        items = evidence.get("items") or evidence.get("evidence") or (evidence if isinstance(evidence, list) else [])
        if isinstance(items, dict):
            items = [items]
        normalized["evidence"] = {
            "items": items,
            "verified_count": evidence.get("verified_count") or sum(1 for e in items if e.get("status") == "verified"),
            "disputed_count": evidence.get("disputed_count") or sum(1 for e in items if e.get("status") == "disputed"),
            "avg_confidence": evidence.get("avg_confidence") or _avg_confidence(items),
            "_source": "evidence_center",
        }

    return normalized


def _avg_sentiment(mentions: list[dict[str, Any]]) -> float:
    if not mentions:
        return 0.5
    vals = [float(m.get("sentiment") or 0.5) for m in mentions]
    return sum(vals) / len(vals)


def _avg_confidence(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.5
    vals = [float(e.get("confidence") or 0.5) for e in items]
    return sum(vals) / len(vals)
