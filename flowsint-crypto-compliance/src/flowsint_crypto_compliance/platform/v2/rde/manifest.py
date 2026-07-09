"""RFC-0016 RDE v2.0 manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.rde.constraints import rde_architectural_constraints
from flowsint_crypto_compliance.platform.v2.rde.sdk import rde_sdk_manifest
from flowsint_crypto_compliance.platform.v2.rde.security import rde_security_manifest
from flowsint_crypto_compliance.platform.v2.rde.types import FactorGroup, RDEStage, RiskLevel


def rde_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0016",
        "schema_version": "2.0.0",
        "title": "Risk & Decision Engine v2.0",
        "title_ru": "Движок риска и поддержки решений",
        "principle_ru": "RDE агрегирует сигналы и объясняет — решение принимает аналитик",
        "pipeline": [s.value for s in RDEStage],
        "factor_groups": [g.value for g in FactorGroup],
        "risk_levels": [r.value for r in RiskLevel],
        "chapters": list(range(1, 21)),
        "input_subsystems": [
            "blockchain_intelligence",
            "crif",
            "icf",
            "knowledge_store",
            "evidence_center",
        ],
        "confidence_dimensions": [
            "independent_sources",
            "quality",
            "completeness",
            "consistency",
            "freshness",
        ],
        "correlation_types": [
            "blockchain_registry",
            "registry_evidence",
            "osint_graph",
            "blockchain_graph",
        ],
        "sdk": rde_sdk_manifest(),
        "security": rde_security_manifest(),
        "architectural_constraints": rde_architectural_constraints(),
        "monitoring_metrics": [
            "assessment_count",
            "rule_events_fired",
            "error_count",
            "avg_latency_ms",
            "success_rate",
            "by_risk_level",
        ],
        "api": {
            "manifest": "/api/platform/v2/rde/manifest",
            "assess": "/api/platform/v2/rde/assess",
            "rules": "/api/platform/v2/rde/rules",
            "rules_evaluate": "/api/platform/v2/rde/rules/evaluate",
            "monitoring": "/api/platform/v2/rde/monitoring",
            "priorities": "/api/platform/v2/rde/priorities",
        },
    }
