"""RFC-0006 Intelligence Memory — Ch.10."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Global templates only — no cross-case conclusion transfer
_MEMORY: dict[str, list[dict[str, Any]]] = {
    "flow_schemes": [],
    "risk_categories": [],
    "behavior_templates": [],
    "correlation_rules": [],
    "analysis_rules": [],
}


def learn_from_case(
    *,
    case_ref: str,
    patterns: list[dict[str, Any]],
    hypotheses: list[dict[str, Any]],
    scores: dict[str, float],
) -> list[dict[str, Any]]:
    """
    Extract generalized rules/templates from a case.
    Conclusions from case A are NOT auto-applied as evidence in case B.
    """
    updates: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()

    for p in patterns:
        code = p.get("code")
        if not code:
            continue
        entry = {
            "kind": "pattern_template",
            "code": code,
            "title_ru": p.get("title_ru"),
            "learned_at": now,
            "source_case_ref": case_ref,
            "generalized": True,
            "not_cross_case_evidence": True,
        }
        if not _exists("analysis_rules", code):
            _MEMORY["analysis_rules"].append(entry)
            updates.append(entry)

    for h in hypotheses:
        code = h.get("code")
        if code and not _exists("correlation_rules", code):
            entry = {
                "kind": "hypothesis_template",
                "code": code,
                "statement_ru": h.get("statement_ru"),
                "learned_at": now,
                "source_case_ref": case_ref,
                "not_cross_case_evidence": True,
            }
            _MEMORY["correlation_rules"].append(entry)
            updates.append(entry)

    weak = min(scores, key=scores.get) if scores else None
    if weak and scores.get(weak, 100) < 50:
        cat = {
            "kind": "risk_category",
            "metric": weak,
            "learned_at": now,
            "source_case_ref": case_ref,
            "hint_ru": f"Типичная зона внимания: {weak}",
        }
        _MEMORY["risk_categories"].append(cat)
        updates.append(cat)

    return updates


def memory_manifest() -> dict[str, Any]:
    return {
        "rule_ru": "Обобщённые шаблоны без переноса выводов между делами",
        "counts": {k: len(v) for k, v in _MEMORY.items()},
        "categories": list(_MEMORY.keys()),
    }


def reset_memory() -> None:
    """Test helper."""
    for k in _MEMORY:
        _MEMORY[k].clear()


def _exists(bucket: str, code: str) -> bool:
    return any(e.get("code") == code for e in _MEMORY.get(bucket, []))
