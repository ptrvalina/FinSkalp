"""RFC-0018 Ch.5 — explanation engine with evidence citations."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.eia.types import Citation
from flowsint_crypto_compliance.platform.v2.rde.explainability import build_explanation


def _extract_evidence_citations(evidence: list[dict[str, Any]]) -> list[Citation]:
    citations: list[Citation] = []
    for item in evidence[:10]:
        eid = item.get("evidence_id") or item.get("id")
        citations.append(
            Citation(
                evidence_id=str(eid) if eid else None,
                source_type=str(item.get("source_type") or item.get("category") or "unknown"),
                label_ru=str(item.get("entity_value") or item.get("label") or item.get("display_name") or "доказательство"),
                confidence=float(item.get("confidence") or item.get("payload", {}).get("confidence") or 0.5),
                excerpt=str(item.get("summary") or "")[:200] or None,
            )
        )
    return citations


def explain_risk(
    *,
    entity_key: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Explain risk level with evidence_ids, confidence, limitations."""
    rde = (context.get("rde_assessments") or {}).get(entity_key) or {}
    explanation = rde.get("explanation") or {}
    evidence = context.get("evidence") or []

    if not explanation and rde.get("ok"):
        signals = rde.get("signals") or {}
        explanation = build_explanation(
            entity_key=entity_key,
            signals=signals,
            factor_results=rde.get("factor_results") or {},
            risk_mapping=rde.get("risk_mapping") or {},
            confidence=rde.get("confidence") or {},
            correlations=rde.get("correlations") or [],
            rule_events=rde.get("rule_events") or [],
        )

    risk_level = (rde.get("risk_mapping") or {}).get("risk_level") or explanation.get("why", {}).get("risk_level")
    composite = (rde.get("confidence") or {}).get("composite") or 0.5
    limitations = list(explanation.get("limitations") or [])
    if not evidence:
        limitations.append("Нет зарегистрированных доказательств для цитирования")

    citations = _extract_evidence_citations(evidence)
    narrative = (
        f"Уровень риска для {entity_key}: {risk_level or 'не определён'}. "
        f"{(explanation.get('why') or {}).get('explanation_ru') or 'Анализ на основе доступных сигналов.'}"
    )

    return {
        "narrative_ru": narrative,
        "explanation": explanation,
        "citations": citations,
        "confidence": composite,
        "limitations": limitations,
        "risk_level": risk_level,
    }


def explain_links(
    *,
    entity_key: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Describe entity links in knowledge graph."""
    neighbors = (context.get("neighbors") or {}).get(entity_key) or []
    evidence = context.get("evidence") or []
    citations = _extract_evidence_citations(evidence)

    if not neighbors:
        return {
            "narrative_ru": f"Для {entity_key} связи в графе знаний не обнаружены.",
            "citations": citations,
            "confidence": 0.3,
            "limitations": ["Граф знаний может быть неполным"],
            "links": [],
        }

    link_descriptions = []
    for nb in neighbors[:15]:
        rel = nb.get("rel_type") or nb.get("relation_type") or "связан"
        target = nb.get("canonical_key") or nb.get("target") or nb.get("label") or "?"
        link_descriptions.append(f"{rel} → {target}")

    narrative = (
        f"Объект {entity_key} имеет {len(neighbors)} связей в графе знаний: "
        + "; ".join(link_descriptions[:5])
        + ("..." if len(link_descriptions) > 5 else "")
    )

    return {
        "narrative_ru": narrative,
        "citations": citations,
        "confidence": min(0.5 + len(neighbors) * 0.05, 0.9),
        "limitations": ["Связи требуют подтверждения аналитиком"],
        "links": neighbors,
    }


def explain_graph_cluster(
    *,
    entity_keys: list[str],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Narrative for a cluster of related entities."""
    all_neighbors: list[dict[str, Any]] = []
    for key in entity_keys:
        all_neighbors.extend((context.get("neighbors") or {}).get(key) or [])

    shared_targets: dict[str, int] = {}
    for nb in all_neighbors:
        target = str(nb.get("canonical_key") or nb.get("target") or "")
        if target:
            shared_targets[target] = shared_targets.get(target, 0) + 1

    cluster_nodes = [t for t, c in shared_targets.items() if c >= 2]
    evidence = context.get("evidence") or []
    citations = _extract_evidence_citations(evidence)

    if cluster_nodes:
        narrative = (
            f"Кластер из {len(entity_keys)} объектов связан через {len(cluster_nodes)} общих узлов: "
            + ", ".join(cluster_nodes[:5])
        )
        confidence = 0.7
    else:
        narrative = f"Объекты {', '.join(entity_keys)} не образуют явного кластера в графе."
        confidence = 0.4

    return {
        "narrative_ru": narrative,
        "citations": citations,
        "confidence": confidence,
        "limitations": ["Кластеризация эвристическая — требует проверки"],
        "cluster_nodes": cluster_nodes,
    }
