"""RFC-0018 Ch.6 — recommendations with explanations (human-in-the-loop)."""

from __future__ import annotations

import uuid
from typing import Any


def build_recommendations(
    *,
    context: dict[str, Any],
    entity_key: str | None = None,
    task_type: str = "summary",
) -> list[dict[str, Any]]:
    """
    Generate analyst recommendations — all require confirmation.
    Reuses RDE decision_support + workflow recommendations.
    """
    recs: list[dict[str, Any]] = []

    # Workflow recommendations
    for wf_rec in context.get("workflow_recommendations") or []:
        recs.append({
            "id": wf_rec.get("id", str(uuid.uuid4())),
            "action": wf_rec.get("id", "workflow_action"),
            "action_ru": wf_rec.get("action_ru", ""),
            "explanation_ru": wf_rec.get("explanation_ru", ""),
            "priority": wf_rec.get("priority", "medium"),
            "requires_analyst_confirmation": True,
            "source": "workflow",
        })

    # RDE recommendations
    if entity_key:
        rde = (context.get("rde_assessments") or {}).get(entity_key) or {}
        for rde_rec in rde.get("recommendations") or []:
            recs.append({
                "id": rde_rec.get("id", str(uuid.uuid4())),
                "action": rde_rec.get("action", "rde_action"),
                "action_ru": rde_rec.get("rationale_ru", rde_rec.get("action", "")),
                "explanation_ru": rde_rec.get("rationale_ru", ""),
                "priority": rde_rec.get("priority", "medium"),
                "requires_analyst_confirmation": True,
                "source": "rde",
            })

    # Task-specific recommendations
    if task_type == "data_gaps":
        missing = _detect_missing_groups(context, entity_key)
        for group in missing:
            recs.append({
                "id": str(uuid.uuid4()),
                "action": f"collect_{group}",
                "action_ru": f"Собрать данные: {group}",
                "explanation_ru": f"Обнаружен пробел в группе сигналов «{group}»",
                "priority": "medium",
                "requires_analyst_confirmation": True,
                "source": "eia",
            })

    if task_type == "contradictions":
        recs.append({
            "id": str(uuid.uuid4()),
            "action": "resolve_contradiction",
            "action_ru": "Сверить противоречивые источники вручную",
            "explanation_ru": "EIA выявил потенциальные противоречия — требуется решение аналитика",
            "priority": "high",
            "requires_analyst_confirmation": True,
            "source": "eia",
        })

    if not recs:
        recs.append({
            "id": str(uuid.uuid4()),
            "action": "review_context",
            "action_ru": "Просмотреть контекст расследования",
            "explanation_ru": "Автоматических рекомендаций нет — проверьте собранные данные",
            "priority": "low",
            "requires_analyst_confirmation": True,
            "source": "eia",
        })

    return recs


def _detect_missing_groups(context: dict[str, Any], entity_key: str | None) -> list[str]:
    all_groups = {"blockchain", "registry", "osint", "graph", "evidence"}
    if not entity_key:
        return list(all_groups)
    rde = (context.get("rde_assessments") or {}).get(entity_key) or {}
    explanation = rde.get("explanation") or {}
    missing = explanation.get("missing") or []
    if missing:
        return missing
    signals = rde.get("signals") or {}
    present = {g for g, s in signals.items() if s}
    return sorted(all_groups - present)
