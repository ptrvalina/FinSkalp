"""RFC-0015 Ch.16 — CRIF SDK manifest."""

from __future__ import annotations

from typing import Any


def crif_sdk_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0015",
        "chapter": 16,
        "extends": "RFC-0007",
        "base_class": "BaseConnector",
        "crif_wrapper": "RegistryConnector",
        "features": [
            "registry_connector_lifecycle",
            "canonical_entity_types",
            "compliance_checks",
            "sanctions_screening",
            "rules_engine",
            "change_history",
            "jurisdiction_intelligence",
            "event_publish_via_bridges",
            "cache_layer",
            "monitoring",
        ],
        "templates": [
            "registry_connector_stub.py",
            "crif_pipeline_integration.py",
            "sanctions_screen_test.py",
            "rules_engine_test.py",
        ],
        "forbidden": [
            "direct_knowledge_graph_mutation",
            "direct_risk_scoring",
            "direct_investigation_mutation",
            "entity_resolution_bypass",
        ],
        "registration": "crif.registry_catalog.register_crif_registry_connectors()",
    }
