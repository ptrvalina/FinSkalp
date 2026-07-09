"""RFC-0018 EIA v2.0 manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.eia.constraints import eia_architectural_constraints
from flowsint_crypto_compliance.platform.v2.eia.model_registry import model_registry_manifest
from flowsint_crypto_compliance.platform.v2.eia.security import eia_security_manifest
from flowsint_crypto_compliance.platform.v2.eia.types import AITaskType, EIAStage


def eia_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0018",
        "schema_version": "2.0.0",
        "title": "Explainable AI & Investigation Assistant v2.0",
        "title_ru": "Объяснимый ИИ и ассистент расследования",
        "principle_ru": "EIA объясняет и рекомендует — решение принимает аналитик",
        "pipeline": [s.value for s in EIAStage],
        "task_types": [t.value for t in AITaskType],
        "engines": [
            "context_engine",
            "prompt_engine",
            "explanation_engine",
            "recommendation_engine",
            "summary_engine",
            "report_assistant",
            "graph_assistant",
            "timeline_assistant",
            "evidence_assistant",
        ],
        "chapters": list(range(1, 21)),
        "input_subsystems": [
            "rde",
            "eccf",
            "knowledge_store",
            "analyst_workspace",
            "workflow",
            "intelligence_engine",
        ],
        "architectural_constraints": eia_architectural_constraints(),
        "security": eia_security_manifest(),
        "model_registry": model_registry_manifest(),
        "monitoring_metrics": [
            "task_count",
            "error_count",
            "avg_latency_ms",
            "success_rate",
            "cache_hits",
            "cache_misses",
            "by_task_type",
        ],
        "api": {
            "manifest": "/api/platform/v2/eia/manifest",
            "assist": "/api/platform/v2/eia/assist",
            "context": "/api/platform/v2/eia/context",
            "prompts": "/api/platform/v2/eia/prompts",
            "monitoring": "/api/platform/v2/eia/monitoring",
        },
    }
