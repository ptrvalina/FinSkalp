"""RFC-0007 Connector SDK — Ch.8."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors.base import BaseConnector
from flowsint_crypto_compliance.platform.v2.connectors.types import ConnectorDescriptor


def sdk_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0007",
        "base_class": "BaseConnector",
        "contract": "Connector",
        "features": [
            "base_interfaces",
            "canonical_models",
            "logging_hooks",
            "error_handling",
            "retry_ready",
            "test_templates",
            "event_publish_via_ingest",
        ],
        "forbidden": [
            "direct_knowledge_graph_mutation",
            "direct_risk_scoring",
            "entity_resolution_bypass",
        ],
    }


def build_connector(descriptor: ConnectorDescriptor) -> BaseConnector:
    return BaseConnector(descriptor)
