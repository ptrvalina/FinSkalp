"""RFC-0017 ECCF v2.0 manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.eccf.access_control import eccf_access_control_manifest
from flowsint_crypto_compliance.platform.v2.eccf.audit_trail import AuditAction
from flowsint_crypto_compliance.platform.v2.eccf.constraints import eccf_architectural_constraints
from flowsint_crypto_compliance.platform.v2.eccf.types import ECCFStage, EvidenceCategory, EvidenceLifecycle


def eccf_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0017",
        "schema_version": "2.0.0",
        "title": "Evidence & Chain of Custody Framework v2.0",
        "title_ru": "Фреймворк доказательств и цепочки хранения",
        "principle_ru": "Доказательства неизменяемы — каждое действие фиксируется в аудите",
        "pipeline": [s.value for s in ECCFStage],
        "evidence_categories": [c.value for c in EvidenceCategory],
        "lifecycle_states": [s.value for s in EvidenceLifecycle],
        "audit_actions": [a.value for a in AuditAction],
        "evidence_id_format": "EV-YYYY-NNNNNNNNNNNN",
        "chapters": list(range(1, 21)),
        "input_subsystems": [
            "icf",
            "crif",
            "blockchain_intelligence",
            "evidence_center",
            "knowledge_store",
            "ingest_pipeline",
        ],
        "access_control": eccf_access_control_manifest(),
        "architectural_constraints": eccf_architectural_constraints(),
        "monitoring_metrics": [
            "registered_count",
            "deduplicated_count",
            "integrity_failures",
            "archived_count",
            "report_usage_count",
            "kg_linked_count",
            "avg_latency_ms",
            "success_rate",
            "by_category",
        ],
        "api": {
            "manifest": "/api/platform/v2/eccf/manifest",
            "register": "/api/platform/v2/eccf/register",
            "evidence": "/api/platform/v2/eccf/{evidence_id}",
            "verify": "/api/platform/v2/eccf/{evidence_id}/verify",
            "audit": "/api/platform/v2/eccf/{evidence_id}/audit",
            "timeline": "/api/platform/v2/eccf/{evidence_id}/timeline",
            "archive": "/api/platform/v2/eccf/{evidence_id}/archive",
            "report_usage": "/api/platform/v2/eccf/report-usage",
            "monitoring": "/api/platform/v2/eccf/monitoring",
        },
    }
