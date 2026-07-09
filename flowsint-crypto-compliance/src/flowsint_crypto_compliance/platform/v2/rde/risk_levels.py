"""RFC-0016 Ch.7 — map numeric score to RiskLevel with transition explanations."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.rde.types import RiskLevel

_THRESHOLDS: list[tuple[float, RiskLevel]] = [
    (80.0, RiskLevel.CRITICAL),
    (60.0, RiskLevel.HIGH),
    (40.0, RiskLevel.MEDIUM),
    (20.0, RiskLevel.LOW),
    (0.0, RiskLevel.INFORMATIONAL),
]

_TRANSITIONS_RU: dict[str, str] = {
    "informational→low": "Появились начальные сигналы, требующие наблюдения",
    "low→medium": "Накоплено достаточно факторов для умеренного внимания",
    "medium→high": "Множественные источники подтверждают повышенный риск",
    "high→critical": "Критические факторы (санкции, миксеры, множественные корреляции)",
    "critical→high": "Снижение критичности — часть факторов ослабла",
    "high→medium": "Снижение риска — уменьшение активности или подтверждений",
    "medium→low": "Минимальные сигналы, преимущественно информационные",
    "low→informational": "Отсутствие значимых сигналов",
}


def map_score_to_risk_level(score: float, *, previous_level: RiskLevel | None = None) -> dict[str, Any]:
    """Map composite score (0–100) to RiskLevel with explanation."""
    level = RiskLevel.INFORMATIONAL
    for threshold, risk in _THRESHOLDS:
        if score >= threshold:
            level = risk
            break

    explanation_ru = _level_explanation(level, score)
    transition: str | None = None
    if previous_level and previous_level != level:
        key = f"{previous_level.value}→{level.value}"
        transition = _TRANSITIONS_RU.get(key, f"Переход {previous_level.value} → {level.value}")

    return {
        "risk_level": level.value,
        "score": round(score, 2),
        "explanation_ru": explanation_ru,
        "transition_ru": transition,
        "previous_level": previous_level.value if previous_level else None,
        "thresholds": {r.value: t for t, r in _THRESHOLDS},
    }


def _level_explanation(level: RiskLevel, score: float) -> str:
    explanations = {
        RiskLevel.INFORMATIONAL: f"Информационный уровень (score={score:.1f}) — минимальные сигналы",
        RiskLevel.LOW: f"Низкий риск (score={score:.1f}) — отдельные факторы требуют мониторинга",
        RiskLevel.MEDIUM: f"Средний риск (score={score:.1f}) — рекомендуется углублённый анализ",
        RiskLevel.HIGH: f"Высокий риск (score={score:.1f}) — приоритетное расследование",
        RiskLevel.CRITICAL: f"Критический риск (score={score:.1f}) — немедленное внимание аналитика",
    }
    return explanations.get(level, f"Уровень {level.value}")
