"""RFC-0015 CRIF v2.0 manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.crif.registry_catalog import registry_connector_catalog
from flowsint_crypto_compliance.platform.v2.crif.sdk import crif_sdk_manifest
from flowsint_crypto_compliance.platform.v2.crif.security import crif_security_manifest
from flowsint_crypto_compliance.platform.v2.crif.sources import registry_source_catalog
from flowsint_crypto_compliance.platform.v2.crif.types import CRIFStage, CanonicalEntityType, ConnectorLifecycle


def crif_manifest() -> dict[str, Any]:
    catalog = registry_connector_catalog()
    return {
        "rfc": "RFC-0015",
        "schema_version": "2.0.0",
        "title": "Compliance & Registry Intelligence Framework v2.0",
        "title_ru": "Фреймворк комплаенс- и реестровой разведки",
        "principle_ru": "Реестр — поставщик юридических фактов, не готовых комплаенс-выводов",
        "pipeline": [s.value for s in CRIFStage],
        "connector_lifecycle": [c.value for c in ConnectorLifecycle],
        "chapters": list(range(1, 21)),
        "source_categories": registry_source_catalog(),
        "registry_connectors": catalog,
        "canonical_entity_types": [e.value for e in CanonicalEntityType],
        "sdk": crif_sdk_manifest(),
        "security": crif_security_manifest(),
        "connector_count": catalog["total"],
        "compliance_checks": [
            "org_exists",
            "registration_valid",
            "licenses_active",
            "restrictions",
            "status_current",
            "cross_source_match",
        ],
        "sanctions_match_types": ["exact", "fuzzy", "transliteration", "probable"],
        "monitoring_metrics": [
            "latency_ms",
            "request_count",
            "error_count",
            "records_processed",
            "checks_run",
            "sanctions_screened",
            "rules_fired",
            "success_rate",
            "connection_status",
        ],
        "architectural_constraints": {
            "connector_forbidden": [
                "mutate_graph",
                "mutate_risk",
                "mutate_investigation",
                "entity_resolution_bypass",
            ],
            "risk_bridge": "emit events only — no direct risk score mutation",
            "workspace_stage": "emit EVIDENCE_CREATED events — no direct workspace mutation",
        },
        "api": {
            "manifest": "/api/platform/v2/crif/manifest",
            "check": "/api/platform/v2/crif/check",
            "sanctions_screen": "/api/platform/v2/crif/sanctions/screen",
            "rules": "/api/platform/v2/crif/rules",
            "rules_evaluate": "/api/platform/v2/crif/rules/evaluate",
            "metrics": "/api/platform/v2/crif/metrics",
            "history": "/api/platform/v2/crif/history/{entity_key}",
        },
    }
