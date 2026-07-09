"""RFC-0016 Ch.9 — decision support recommendations (NOT decisions)."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.rde.types import DecisionRecommendation, RiskLevel


def generate_recommendations(
    *,
    entity_key: str,
    risk_level: RiskLevel,
    signals: dict[str, dict[str, Any]],
    correlations: list[dict[str, Any]],
    rule_events: list[dict[str, Any]],
) -> list[DecisionRecommendation]:
    """
    Generate analyst recommendations — never auto-decisions.
    All recommendations require analyst confirmation.
    """
    recs: list[DecisionRecommendation] = []

    if risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL):
        recs.append(
            DecisionRecommendation(
                id=str(uuid.uuid4()),
                action="expand_time_range",
                priority="high" if risk_level == RiskLevel.CRITICAL else "medium",
                rationale_ru="Расширить временной диапазон анализа для выявления паттернов",
                requires_analyst=True,
                metadata={"entity_key": entity_key, "suggested_days": 90},
            )
        )

    registry = signals.get("registry") or {}
    if registry or any(c.get("type") == "registry_evidence" for c in correlations):
        recs.append(
            DecisionRecommendation(
                id=str(uuid.uuid4()),
                action="check_documents",
                priority="medium",
                rationale_ru="Проверить регистрационные документы и лицензии",
                requires_analyst=True,
                metadata={"organization": registry.get("organization")},
            )
        )

    graph = signals.get("graph") or {}
    if graph.get("neighbors") or any(c.get("type") in ("osint_graph", "blockchain_graph") for c in correlations):
        recs.append(
            DecisionRecommendation(
                id=str(uuid.uuid4()),
                action="investigate_related_orgs",
                priority="medium",
                rationale_ru="Исследовать связанные организации в графе знаний",
                requires_analyst=True,
                metadata={"neighbor_count": len(graph.get("neighbors") or [])},
            )
        )

    if registry or risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        recs.append(
            DecisionRecommendation(
                id=str(uuid.uuid4()),
                action="refresh_registries",
                priority="high" if risk_level == RiskLevel.CRITICAL else "low",
                rationale_ru="Обновить данные из реестров (CRIF sync)",
                requires_analyst=True,
            )
        )

    if rule_events:
        recs.append(
            DecisionRecommendation(
                id=str(uuid.uuid4()),
                action="review_rule_events",
                priority="high",
                rationale_ru=f"Просмотреть {len(rule_events)} сработавших правил",
                requires_analyst=True,
                metadata={"event_count": len(rule_events)},
            )
        )

    if not signals.get("blockchain"):
        recs.append(
            DecisionRecommendation(
                id=str(uuid.uuid4()),
                action="collect_blockchain_signals",
                priority="low",
                rationale_ru="Собрать блокчейн-сигналы для полноты оценки",
                requires_analyst=True,
            )
        )

    return recs
