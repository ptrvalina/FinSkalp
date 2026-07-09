"""RFC-0018 Ch.10 — timeline analysis assistant."""

from __future__ import annotations

from typing import Any


def build_timeline_analysis(context: dict[str, Any]) -> dict[str, Any]:
    """Analyze timeline events and explain changes."""
    case_ref = context.get("case_ref", "")
    events = context.get("timeline") or []

    if not events:
        return {
            "narrative_ru": f"Хронология дела {case_ref} пуста — события не зарегистрированы.",
            "events": [],
            "confidence": 0.2,
            "limitations": ["Нет данных для анализа хронологии"],
            "change_summary": [],
        }

    event_types: dict[str, int] = {}
    for ev in events:
        etype = str(ev.get("event_type") or ev.get("type") or "unknown")
        event_types[etype] = event_types.get(etype, 0) + 1

    type_summary = ", ".join(f"{k}: {v}" for k, v in sorted(event_types.items(), key=lambda x: -x[1])[:5])
    narrative = (
        f"Хронология дела {case_ref}: {len(events)} событий. "
        f"Типы: {type_summary}."
    )

    change_summary = []
    for ev in events[:10]:
        change_summary.append({
            "event_type": ev.get("event_type") or ev.get("type"),
            "occurred_at": ev.get("occurred_at") or ev.get("timestamp"),
            "actor": ev.get("actor"),
            "label": ev.get("label") or ev.get("description"),
        })

    return {
        "narrative_ru": narrative,
        "events": events,
        "change_summary": change_summary,
        "confidence": min(0.4 + len(events) * 0.02, 0.85),
        "limitations": ["Хронология может быть неполной"],
    }
