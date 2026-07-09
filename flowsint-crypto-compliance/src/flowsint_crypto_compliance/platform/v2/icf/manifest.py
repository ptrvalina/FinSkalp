"""RFC-0014 ICF v2.0 manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors import get_connector_registry
from flowsint_crypto_compliance.platform.v2.icf.lifecycle import lifecycle_manifest
from flowsint_crypto_compliance.platform.v2.icf.sdk import icf_sdk_manifest
from flowsint_crypto_compliance.platform.v2.icf.security import icf_security_manifest
from flowsint_crypto_compliance.platform.v2.icf.sources import source_category_registry
from flowsint_crypto_compliance.platform.v2.icf.types import CollectorLifecycle, ICFStage


def icf_manifest() -> dict[str, Any]:
    connectors = get_connector_registry().list_descriptors()
    return {
        "rfc": "RFC-0014",
        "schema_version": "2.0.0",
        "title": "Intelligence Collection Framework v2.0",
        "title_ru": "Фреймворк интеллектуального сбора информации",
        "principle_ru": "Источник — поставщик фактов, не готовых выводов",
        "pipeline": [s.value for s in ICFStage],
        "collector_lifecycle": [c.value for c in CollectorLifecycle],
        "chapters": list(range(1, 21)),
        "source_categories": source_category_registry(),
        "lifecycle": lifecycle_manifest(),
        "sdk": icf_sdk_manifest(),
        "security": icf_security_manifest(),
        "collector_count": len(connectors),
        "quality_dimensions": [
            "completeness",
            "freshness",
            "origin",
            "stability",
            "error_rate",
            "structure",
            "repeatability",
        ],
        "monitoring_metrics": [
            "latency_ms",
            "request_count",
            "error_count",
            "records_processed",
            "success_rate",
            "connection_status",
        ],
        "architectural_constraints": {
            "collector_forbidden": [
                "mutate_graph",
                "mutate_risk",
                "entity_resolution",
                "analytical_decisions",
            ],
        },
        "api": {
            "manifest": "/api/platform/v2/icf/manifest",
            "collect": "/api/platform/v2/icf/collect",
            "scheduler_status": "/api/platform/v2/icf/scheduler/status",
            "scheduler_schedule": "/api/platform/v2/icf/scheduler/schedule",
            "monitoring": "/api/platform/v2/icf/monitoring",
        },
    }
