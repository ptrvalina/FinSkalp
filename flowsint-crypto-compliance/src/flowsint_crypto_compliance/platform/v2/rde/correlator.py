"""RFC-0016 Ch.12 — cross-domain correlation."""

from __future__ import annotations

from typing import Any, Callable


def _correlate_blockchain_docs(
    blockchain: dict[str, Any], registry: dict[str, Any]
) -> dict[str, Any] | None:
    if not blockchain or not registry:
        return None
    org = registry.get("organization") or registry.get("entity_value")
    address = blockchain.get("address")
    if not org and not address:
        return None
    confidence = 0.6
    if registry.get("sanctioned"):
        confidence = 0.85
    if blockchain.get("mixer_exposure"):
        confidence = min(0.95, confidence + 0.1)
    return {
        "type": "blockchain_registry",
        "description_ru": "Связь блокчейн-активности с реестровыми данными",
        "confidence": round(confidence, 3),
        "entities": {"address": address, "organization": org},
    }


def _correlate_docs_orgs(registry: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any] | None:
    if not registry or not evidence:
        return None
    items = evidence.get("items") or []
    org = registry.get("organization")
    if not org or not items:
        return None
    matching = [e for e in items if org.lower() in str(e.get("entity_value") or e.get("title") or "").lower()]
    if not matching:
        return None
    return {
        "type": "registry_evidence",
        "description_ru": "Документальные доказательства подтверждают реестровую сущность",
        "confidence": round(min(0.9, 0.5 + len(matching) * 0.1), 3),
        "match_count": len(matching),
    }


def _correlate_osint_graph(osint: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any] | None:
    if not osint or not graph:
        return None
    mentions = osint.get("mentions") or []
    neighbors = graph.get("neighbors") or []
    if not mentions or not neighbors:
        return None
    return {
        "type": "osint_graph",
        "description_ru": "OSINT-упоминания коррелируют с графовыми связями",
        "confidence": round(min(0.85, 0.4 + len(mentions) * 0.05 + len(neighbors) * 0.03), 3),
        "mention_count": len(mentions),
        "neighbor_count": len(neighbors),
    }


def _correlate_blockchain_graph(blockchain: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any] | None:
    if not blockchain or not graph:
        return None
    address = blockchain.get("address")
    neighbors = graph.get("neighbors") or []
    if not address or not neighbors:
        return None
    linked = [n for n in neighbors if address.lower() in str(n.get("entity", {}).get("canonical_key") or "").lower()]
    if not linked:
        return None
    return {
        "type": "blockchain_graph",
        "description_ru": "Адрес блокчейна связан с узлами графа знаний",
        "confidence": round(min(0.9, 0.55 + len(linked) * 0.08), 3),
        "link_count": len(linked),
    }


_CUSTOM_CORRELATIONS: list[Callable[[dict[str, dict[str, Any]]], dict[str, Any] | None]] = []


def correlate_signals(signals: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Run cross-domain correlations with per-correlation confidence."""
    correlations: list[dict[str, Any]] = []
    blockchain = signals.get("blockchain") or {}
    registry = signals.get("registry") or {}
    osint = signals.get("osint") or {}
    graph = signals.get("graph") or {}
    evidence = signals.get("evidence") or {}

    for fn in (
        lambda: _correlate_blockchain_docs(blockchain, registry),
        lambda: _correlate_docs_orgs(registry, evidence),
        lambda: _correlate_osint_graph(osint, graph),
        lambda: _correlate_blockchain_graph(blockchain, graph),
    ):
        hit = fn()
        if hit:
            correlations.append(hit)

    for custom in _CUSTOM_CORRELATIONS:
        hit = custom(signals)
        if hit:
            correlations.append(hit)

    return correlations


def register_correlation(fn: Callable[[dict[str, dict[str, Any]]], dict[str, Any] | None]) -> None:
    """SDK extension point — register custom correlation rule."""
    _CUSTOM_CORRELATIONS.append(fn)
