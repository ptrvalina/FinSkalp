"""RFC-0016 Ch.10 — rank investigation objects."""

from __future__ import annotations

from typing import Any


def prioritize_investigation_objects(
    *,
    entity_key: str,
    case_ref: str | None,
    factor_scores: dict[str, float],
    correlations: list[dict[str, Any]],
    rule_events: list[dict[str, Any]],
    composite_score: float,
) -> list[dict[str, Any]]:
    """Rank investigation objects by urgency and relevance."""
    objects: list[dict[str, Any]] = []

    objects.append({
        "object_type": "entity",
        "object_key": entity_key,
        "priority_score": round(composite_score, 2),
        "urgency": _urgency(composite_score),
        "rationale_ru": "Основной объект оценки",
    })

    for corr in correlations:
        objects.append({
            "object_type": "correlation",
            "object_key": corr.get("type", "unknown"),
            "priority_score": round((corr.get("confidence") or 0) * 100, 2),
            "urgency": _urgency((corr.get("confidence") or 0) * 100),
            "rationale_ru": corr.get("description_ru", "Кросс-доменная корреляция"),
        })

    for event in rule_events:
        severity_weight = {"critical": 95, "high": 75, "medium": 50, "low": 25}.get(event.get("severity", "medium"), 50)
        objects.append({
            "object_type": "rule_event",
            "object_key": event.get("rule_id", "unknown"),
            "priority_score": severity_weight,
            "urgency": _urgency(severity_weight),
            "rationale_ru": event.get("message_ru", "Сработавшее правило"),
        })

    for group, score in factor_scores.items():
        if score > 30:
            objects.append({
                "object_type": "factor_group",
                "object_key": group,
                "priority_score": round(score, 2),
                "urgency": _urgency(score),
                "rationale_ru": f"Факторная группа {group} с повышенным score",
            })

    objects.sort(key=lambda o: o["priority_score"], reverse=True)

    if case_ref:
        for obj in objects:
            obj["case_ref"] = case_ref

    return objects


def _urgency(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 20:
        return "low"
    return "informational"
