"""RFC-0016 Ch.18 — architectural constraints and forbidden actions."""

from __future__ import annotations

from typing import Any


def rde_architectural_constraints() -> dict[str, Any]:
    return {
        "forbidden_actions": [
            "mutate_source_data",
            "mutate_knowledge_graph",
            "mutate_evidence_center",
            "auto_decision",
            "direct_risk_score_mutation",
            "direct_investigation_mutation",
            "bypass_analyst_review",
        ],
        "forbidden_modules": [
            "flowsint_crypto_compliance.platform.v2.knowledge_graph",
            "flowsint_crypto_compliance.platform.v2.investigation_platform",
            "flowsint_crypto_compliance.platform.v2.investigation_workspace",
        ],
        "principle": "RDE aggregates and explains — analyst decides",
        "principle_ru": "RDE агрегирует сигналы и объясняет — решение принимает аналитик",
        "read_only_subsystems": [
            "blockchain_intelligence",
            "crif",
            "icf",
            "knowledge_store",
            "evidence_center",
        ],
    }
