"""RFC-0012 manifest — Blockchain Intelligence Framework v2.0."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.canonical_model import (
    CANONICAL_ENTITIES,
    CLUSTERING_METHODS,
    PIPELINE_STAGES,
    SUPPORTED_NETWORKS,
)
from flowsint_crypto_compliance.platform.v2.intelligence.blockchain_capabilities import (
    RFC_CHAIN_CAPABILITIES,
)

ADAPTER_FUNCTIONS = [
    "connect",
    "sync_blocks",
    "import_transactions",
    "import_addresses",
    "import_tokens",
    "import_internal_transactions",
    "publish_events",
]

SECURITY_CONTROLS = [
    "secure_config_storage",
    "integration_access_control",
    "operation_audit_log",
    "data_integrity_checks",
    "error_monitoring",
]

MONITORING_METRICS = [
    "sync_speed_blocks_per_sec",
    "blocks_processed",
    "transactions_processed",
    "error_count",
    "processing_lag_ms",
    "source_availability",
]


def blockchain_intelligence_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0012",
        "schema_version": "12.0.0",
        "title": "Blockchain Intelligence Framework v2.0",
        "status": "complete",
        "canonical_entities": list(CANONICAL_ENTITIES),
        "supported_networks": SUPPORTED_NETWORKS,
        "adapter_contract": ADAPTER_FUNCTIONS,
        "pipeline_stages": PIPELINE_STAGES,
        "clustering_methods": CLUSTERING_METHODS,
        "capabilities": list(RFC_CHAIN_CAPABILITIES),
        "security_controls": SECURITY_CONTROLS,
        "monitoring_metrics": MONITORING_METRICS,
        "incremental_sync": {
            "enabled": True,
            "rfc": "RFC-0013",
            "celery_task": "sync_blockchain_chains_incremental",
            "beat_interval_seconds": 120,
            "endpoints": {
                "status": "/api/platform/v2/blockchain-intelligence/sync/status",
                "run": "/api/platform/v2/blockchain-intelligence/sync/run",
            },
        },
        "explainable": True,
        "principle_ru": (
            "Блокчейн-данные нормализуются в каноническую модель и публикуются в Knowledge Graph "
            "с объяснимой аналитикой — без автономных юридических решений."
        ),
        "rule_ru": "Адаптер не выполняет анализ риска — только импорт и публикация событий",
    }
