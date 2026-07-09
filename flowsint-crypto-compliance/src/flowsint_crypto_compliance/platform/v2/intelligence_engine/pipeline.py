"""RFC-0006 Intelligence Pipeline — Ch.2."""

from __future__ import annotations

from typing import Any

RFC0006_PIPELINE: list[str] = [
    "source",
    "collector",
    "normalizer",
    "validator",
    "entity_resolution",
    "knowledge_graph",
    "correlation",
    "pattern_detection",
    "behavior_analysis",
    "risk",
    "hypothesis_generator",
    "ai_explanation",
    "investigation",
    "report",
]

_PIPELINE_LABELS_RU: dict[str, str] = {
    "source": "Источник",
    "collector": "Collector",
    "normalizer": "Normalizer",
    "validator": "Validator",
    "entity_resolution": "Entity Resolution",
    "knowledge_graph": "Knowledge Graph",
    "correlation": "Correlation",
    "pattern_detection": "Pattern Detection",
    "behavior_analysis": "Behavior Analysis",
    "risk": "Risk",
    "hypothesis_generator": "Hypothesis Generator",
    "ai_explanation": "AI Explanation",
    "investigation": "Investigation",
    "report": "Report",
}

FUSION_INTELLIGENCE_STAGES: list[str] = [
    "source",
    "type",
    "trust",
    "relations",
    "conflicts",
    "duplicates",
    "priority",
    "context",
    "impact",
    "entity",
    "evidence",
    "graph",
]

PHILOSOPHY_QUESTIONS_RU: list[str] = [
    "Что произошло?",
    "Почему произошло?",
    "Кто участвовал?",
    "Что может быть связано?",
    "Что следует проверить дальше?",
]


def intelligence_pipeline_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0006",
        "schema_version": "6.0.0",
        "title": "Intelligence Engine",
        "philosophy_ru": "Искать неизвестные взаимосвязи, а не информацию",
        "questions_ru": PHILOSOPHY_QUESTIONS_RU,
        "pipeline": [
            {"id": s, "label_ru": _PIPELINE_LABELS_RU.get(s, s)}
            for s in RFC0006_PIPELINE
        ],
        "fusion_intelligence": FUSION_INTELLIGENCE_STAGES,
        "rule_ru": "Никаких исключений — вся информация проходит единый путь",
        "score_metrics": [
            "identity_confidence",
            "evidence_strength",
            "relationship_confidence",
            "behavior_stability",
            "source_reliability",
            "case_completeness",
            "hypothesis_confidence",
            "investigation_progress",
        ],
    }
