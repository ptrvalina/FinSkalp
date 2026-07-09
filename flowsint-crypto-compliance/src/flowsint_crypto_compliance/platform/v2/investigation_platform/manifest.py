"""RFC-0005 Investigation Platform manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.investigation_platform.types import ReportKind, WorkspacePanel
from flowsint_crypto_compliance.services.case_workflow import RFC_0005_LIFECYCLE


def investigation_platform_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0005",
        "schema_version": "5.0.0",
        "title": "Investigation Platform & Enterprise Operations v2.0",
        "principle_ru": "Пользователь работает исключительно с расследованием",
        "lifecycle_stages": RFC_0005_LIFECYCLE,
        "workspace_panels": [p.value for p in WorkspacePanel],
        "report_kinds": [r.value for r in ReportKind],
        "evidence_rules": {
            "delete_forbidden": True,
            "status_change_only": True,
            "fields": [
                "id", "source", "discovered_at", "acquisition_method", "author",
                "content_hash", "trust_level", "entity_id", "status_history",
            ],
        },
        "security": [
            "rbac", "abac_ready", "mfa_ready", "audit_log", "evidence_integrity",
            "secrets_vault", "document_versioning", "encryption", "backup", "api_access_control",
        ],
        "operations": [
            "containerization", "orchestration", "centralized_logging", "monitoring",
            "distributed_tracing", "autoscaling", "ha", "backup", "performance_control", "rolling_updates",
        ],
        "observability": [
            "technical_metrics", "business_metrics", "logs", "events", "performance_indicators",
        ],
        "api": {
            "manifest": "/api/platform/v2/investigation/manifest",
            "workspace": "GET /api/platform/v2/investigations/{case_ref}/workspace",
            "evidence": "GET|POST /api/platform/v2/investigations/{case_ref}/evidence",
            "evidence_status": "PATCH /api/platform/v2/evidence/{evidence_id}/status",
            "timeline": "GET /api/platform/v2/investigations/{case_ref}/timeline",
            "explain": "GET /api/platform/v2/investigations/{case_ref}/explain/{entity_id}",
            "operations": "/api/platform/v2/operations/manifest",
        },
    }


def operations_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0005",
        "chapters": ["security", "operations", "observability", "platform_as_product"],
        "metrics_endpoint": "/api/compliance/metrics",
        "dashboard_read_model": "/api/compliance/dashboard/read-model",
        "event_stream": "/api/compliance/events/stream",
        "tracing": "OTLP via flowsint_crypto_compliance.observability.tracing",
        "grafana": "infra/grafana/dashboards/finskalp-pipeline.json",
        "release_cycle": [
            "architectural_analysis", "design", "implementation", "testing",
            "security_review", "performance_review", "documentation", "deployment", "post_release_analysis",
        ],
    }
