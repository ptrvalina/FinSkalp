"""RFC-0018 Ch.7+18 — architectural constraints and forbidden actions."""

from __future__ import annotations

from typing import Any


_FORBIDDEN_ACTIONS = frozenset({
    "mutate_knowledge_graph",
    "mutate_evidence",
    "mutate_risk_score",
    "auto_decision",
    "auto_close_case",
    "bypass_analyst_review",
    "direct_investigation_mutation",
    "silent_data_write",
})


def eia_architectural_constraints() -> dict[str, Any]:
    return {
        "forbidden_actions": sorted(_FORBIDDEN_ACTIONS),
        "forbidden_modules": [
            "flowsint_crypto_compliance.platform.v2.knowledge_graph",
            "flowsint_crypto_compliance.platform.v2.investigation_platform",
            "flowsint_crypto_compliance.platform.v2.eccf.repository",
            "flowsint_crypto_compliance.platform.v2.rde.temporal",
        ],
        "principle": "EIA explains and recommends — analyst decides",
        "principle_ru": "EIA объясняет и рекомендует — решение принимает аналитик",
        "read_only_subsystems": [
            "knowledge_store",
            "eccf",
            "rde",
            "analyst_workspace",
            "workflow",
            "intelligence_engine",
        ],
        "human_in_the_loop": True,
        "auto_decisions": False,
    }


def assert_not_forbidden(action: str) -> None:
    if action in _FORBIDDEN_ACTIONS:
        raise PermissionError(f"EIA forbidden action: {action}")
