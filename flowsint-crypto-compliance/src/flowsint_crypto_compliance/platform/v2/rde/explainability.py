"""RFC-0016 Ch.8 — explainability engine."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.rde.types import RiskLevel


def build_explanation(
    *,
    entity_key: str,
    signals: dict[str, dict[str, Any]],
    factor_results: dict[str, dict[str, Any]],
    risk_mapping: dict[str, Any],
    confidence: dict[str, Any],
    correlations: list[dict[str, Any]],
    rule_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Answer why/facts/rules/sources/missing/limitations."""
    active_groups = [g for g, s in signals.items() if s]
    missing_groups = [g for g in ("blockchain", "registry", "osint", "graph", "evidence") if g not in active_groups]

    top_factors = sorted(
        [(g, r.get("score", 0)) for g, r in factor_results.items()],
        key=lambda x: x[1],
        reverse=True,
    )[:3]

    facts: list[dict[str, Any]] = []
    for group, data in signals.items():
        if not data:
            continue
        facts.append({
            "group": group,
            "source": data.get("_source", "unknown"),
            "signal_count": len(data.get("signals_used") or data.keys()),
            "summary_ru": _group_summary_ru(group, data),
        })

    sources = [
        {"group": g, "source": signals[g].get("_source"), "fields": list(signals[g].keys())}
        for g in active_groups
    ]

    limitations: list[str] = []
    if missing_groups:
        limitations.append(f"Отсутствуют сигналы: {', '.join(missing_groups)}")
    if confidence.get("composite", 0) < 0.5:
        limitations.append("Низкая уверенность — рекомендуется сбор дополнительных данных")
    if not correlations:
        limitations.append("Кросс-доменные корреляции не обнаружены")

    return {
        "why": {
            "risk_level": risk_mapping.get("risk_level"),
            "explanation_ru": risk_mapping.get("explanation_ru"),
            "top_factors": [{"group": g, "score": s} for g, s in top_factors],
            "composite_score": risk_mapping.get("score"),
        },
        "facts": facts,
        "rules_fired": [{"rule_id": e.get("rule_id"), "message_ru": e.get("message_ru")} for e in rule_events],
        "sources": sources,
        "missing": missing_groups,
        "limitations": limitations,
        "entity_key": entity_key,
        "correlation_summary": [
            {"type": c.get("type"), "confidence": c.get("confidence"), "description_ru": c.get("description_ru")}
            for c in correlations
        ],
    }


def _group_summary_ru(group: str, data: dict[str, Any]) -> str:
    summaries = {
        "blockchain": f"Блокчейн: {data.get('transaction_count', 0)} транзакций",
        "registry": f"Реестр: статус {data.get('org_status', 'неизвестен')}",
        "osint": f"OSINT: {len(data.get('mentions') or [])} упоминаний",
        "graph": f"Граф: {len(data.get('neighbors') or [])} связей",
        "evidence": f"Доказательства: {len(data.get('items') or [])} элементов",
    }
    return summaries.get(group, f"Группа {group}")
