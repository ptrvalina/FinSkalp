"""RFC-0016 Ch.19 — RDE SDK extensibility manifest."""

from __future__ import annotations

from typing import Any


def rde_sdk_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0016",
        "chapter": 19,
        "extends": ["RFC-0006", "RFC-0012", "RFC-0014", "RFC-0015"],
        "entry_point": "run_rde_assessment",
        "features": [
            "factor_group_calculators",
            "cross_domain_correlator",
            "confidence_scoring",
            "risk_level_mapping",
            "explainability_engine",
            "declarative_rules_engine",
            "decision_support_recommendations",
            "investigation_prioritization",
            "temporal_analysis",
            "monitoring_metrics",
        ],
        "extension_points": [
            "factors.register_calculator(group, fn)",
            "correlator.register_correlation(type, fn)",
            "rules_engine.add_rule(rule)",
            "decision_support.add_recommendation_template(template)",
        ],
        "templates": [
            "factor_calculator_stub.py",
            "correlation_rule_stub.py",
            "rde_assessment_test.py",
            "rules_engine_test.py",
        ],
        "forbidden": [
            "mutate_source_data",
            "mutate_knowledge_graph",
            "mutate_evidence_center",
            "auto_decision",
            "direct_risk_score_mutation",
        ],
    }
