"""RFC-0014 Ch.14–15 — Connector SDK manifest."""

from __future__ import annotations

from typing import Any


def icf_sdk_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0014",
        "chapter": 15,
        "extends": "RFC-0007",
        "base_class": "BaseConnector",
        "icf_wrapper": "ICFCollector",
        "features": [
            "base_interfaces",
            "canonical_models",
            "logging_hooks",
            "error_handling",
            "retry_ready",
            "test_templates",
            "event_publish_via_orchestrator",
            "quality_engine_integration",
            "scheduler_registration",
        ],
        "templates": [
            "connector_stub.py",
            "collector_test_template.py",
            "normalizer_override.py",
            "validator_override.py",
            "icf_pipeline_integration.py",
        ],
        "forbidden": [
            "direct_knowledge_graph_mutation",
            "direct_risk_scoring",
            "entity_resolution_bypass",
            "analytical_decisions",
        ],
        "registration": "connectors.registry.register() + icf.scheduler.schedule()",
    }
