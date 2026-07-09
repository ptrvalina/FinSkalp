"""RFC-0011 Ch.9 — workflow recommendations."""

from __future__ import annotations

from typing import Any


def build_recommendations(
    *,
    case_ref: str,
    workflow_stage: str,
    risk_score: float | None = None,
    entity_count: int = 0,
    evidence_count: int = 0,
    hypotheses: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    if workflow_stage in ("case_creation", "object_definition", "auto_collection"):
        recs.append(
            {
                "id": "run_collectors",
                "action_ru": "Запустить автоматический сбор данных",
                "explanation_ru": "После создания дела система собирает blockchain, OSINT и реестры без ручного запуска",
                "priority": "high",
                "phase": "investigate",
            }
        )
    if entity_count == 0:
        recs.append(
            {
                "id": "define_seed",
                "action_ru": "Определить объект расследования",
                "explanation_ru": "Укажите адрес, организацию или документ — запустится цепочка collectors",
                "priority": "high",
                "phase": "observe",
            }
        )
    if evidence_count > 0:
        recs.append(
            {
                "id": "review_evidence",
                "action_ru": "Проверить новые доказательства",
                "explanation_ru": f"В деле {case_ref} зарегистрировано {evidence_count} доказательств",
                "priority": "medium",
                "phase": "correlate",
            }
        )
    if risk_score is not None and risk_score >= 70:
        recs.append(
            {
                "id": "explain_risk",
                "action_ru": "Открыть объяснение риска",
                "explanation_ru": f"Risk Score {risk_score:.0f}/100 — требуется проверка правил и источников",
                "priority": "high",
                "phase": "decide",
            }
        )
    recs.append(
        {
            "id": "build_graph",
            "action_ru": "Построить граф связей",
            "explanation_ru": "Визуализация связей обновит Timeline, Risk и Evidence синхронно",
            "priority": "medium",
            "phase": "correlate",
        }
    )
    for hyp in (hypotheses or [])[:3]:
        recs.append(
            {
                "id": f"hypothesis_{hyp.get('id', 'x')}",
                "action_ru": f"Проверить гипотезу: {hyp.get('statement_ru', '')[:80]}",
                "explanation_ru": f"Уверенность {hyp.get('confidence', 0):.0%} — требует подтверждения аналитиком",
                "priority": "medium",
                "phase": "decide",
            }
        )
    return recs
