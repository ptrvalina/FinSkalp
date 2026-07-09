"""RFC-0018 Ch.8 — investigation brief / summary engine."""

from __future__ import annotations

from typing import Any


def build_investigation_brief(context: dict[str, Any]) -> dict[str, Any]:
    """Generate investigation brief from multi-source context."""
    case_ref = context.get("case_ref", "")
    case = context.get("case") or {}
    entity_keys = context.get("entity_keys") or []
    evidence_count = context.get("evidence_count", 0)
    timeline = context.get("timeline") or []
    hypotheses = context.get("hypotheses") or []

    stage = case.get("workflow_stage", "unknown")
    risk_summary = _summarize_risk(context)

    narrative = (
        f"Дело {case_ref} — стадия «{stage}». "
        f"Объектов: {len(entity_keys)}. Доказательств: {evidence_count}. "
        f"Событий в хронологии: {len(timeline)}. "
        f"{risk_summary} "
        f"Гипотез: {len(hypotheses)}. "
        "Все выводы требуют подтверждения аналитиком."
    )

    return {
        "narrative_ru": narrative,
        "brief": {
            "case_ref": case_ref,
            "stage": stage,
            "entity_count": len(entity_keys),
            "evidence_count": evidence_count,
            "timeline_count": len(timeline),
            "hypothesis_count": len(hypotheses),
            "risk_summary": risk_summary,
        },
        "confidence": 0.6,
        "limitations": ["Краткое резюме — не заменяет полный анализ"],
    }


def _summarize_risk(context: dict[str, Any]) -> str:
    assessments = context.get("rde_assessments") or {}
    if not assessments:
        return "Оценка риска не выполнена."
    levels = []
    for key, assess in assessments.items():
        level = (assess.get("risk_mapping") or {}).get("risk_level")
        if level:
            levels.append(f"{key}: {level}")
    if levels:
        return "Риски: " + ", ".join(levels) + "."
    return "Оценка риска в процессе."
