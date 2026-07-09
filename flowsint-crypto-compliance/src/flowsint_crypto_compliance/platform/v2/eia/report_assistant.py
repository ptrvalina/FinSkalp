"""RFC-0018 Ch.12 — report draft outline + materials + open questions."""

from __future__ import annotations

from typing import Any


def build_report_outline(context: dict[str, Any]) -> dict[str, Any]:
    """Report draft outline, materials list, open questions."""
    case_ref = context.get("case_ref", "")
    evidence = context.get("evidence") or []
    entity_keys = context.get("entity_keys") or []
    hypotheses = context.get("hypotheses") or []
    timeline = context.get("timeline") or []

    sections = [
        {"id": "intro", "title_ru": "Введение", "status": "draft"},
        {"id": "objects", "title_ru": "Объекты расследования", "status": "draft", "count": len(entity_keys)},
        {"id": "timeline", "title_ru": "Хронология", "status": "draft", "count": len(timeline)},
        {"id": "evidence", "title_ru": "Доказательная база", "status": "draft", "count": len(evidence)},
        {"id": "risk", "title_ru": "Оценка рисков", "status": "draft"},
        {"id": "hypotheses", "title_ru": "Гипотезы", "status": "draft", "count": len(hypotheses)},
        {"id": "conclusions", "title_ru": "Выводы", "status": "pending_analyst"},
        {"id": "appendix", "title_ru": "Приложения", "status": "draft"},
    ]

    materials = []
    for ev in evidence[:20]:
        eid = ev.get("evidence_id") or ev.get("id")
        materials.append({
            "evidence_id": str(eid) if eid else None,
            "source_type": ev.get("source_type") or ev.get("category"),
            "label": ev.get("entity_value") or ev.get("label") or "доказательство",
        })

    open_questions = [
        f"Подтвердить связь объектов: {', '.join(entity_keys[:3])}" if entity_keys else "Определить объекты расследования",
        "Сверить уровень риска с доказательной базой",
        "Проверить гипотезы на основании новых данных",
    ]
    for hyp in hypotheses[:3]:
        open_questions.append(f"Гипотеза: {hyp.get('statement_ru', '')[:100]}")

    narrative = (
        f"Черновик отчёта по делу {case_ref}: {len(sections)} разделов, "
        f"{len(materials)} материалов, {len(open_questions)} открытых вопросов."
    )

    return {
        "narrative_ru": narrative,
        "outline": sections,
        "materials": materials,
        "open_questions": open_questions,
        "confidence": 0.5,
        "limitations": ["Черновик — требует редактирования аналитиком"],
    }
