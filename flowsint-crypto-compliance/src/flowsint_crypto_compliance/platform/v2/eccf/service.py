"""RFC-0017 ECCF service facade."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.eccf.archive import archive_evidence, search_archive
from flowsint_crypto_compliance.platform.v2.eccf.audit_trail import get_audit_trail
from flowsint_crypto_compliance.platform.v2.eccf.integrity import verify_integrity
from flowsint_crypto_compliance.platform.v2.eccf.manifest import eccf_manifest
from flowsint_crypto_compliance.platform.v2.eccf.monitoring import get_eccf_metrics
from flowsint_crypto_compliance.platform.v2.eccf.orchestrator import run_eccf_pipeline
from flowsint_crypto_compliance.platform.v2.eccf.report_bridge import record_report_usage
from flowsint_crypto_compliance.platform.v2.eccf.repository import get_eccf_repository
from flowsint_crypto_compliance.platform.v2.eccf.timeline import get_evidence_timeline
from flowsint_crypto_compliance.platform.v2.eccf.versioning import create_new_version


class ECCFService:
    """Evidence & Chain of Custody Framework service."""

    def manifest(self) -> dict[str, Any]:
        return eccf_manifest()

    async def register(
        self,
        *,
        tenant_id: uuid.UUID,
        collector_payload: dict[str, Any],
        case_ref: str | None = None,
        actor: str = "eccf.api",
        source_uri: str | None = None,
        collector_id: str | None = None,
        bridge_kg: bool = True,
    ) -> dict[str, Any]:
        result = await run_eccf_pipeline(
            tenant_id=tenant_id,
            collector_payload=collector_payload,
            case_ref=case_ref,
            actor=actor,
            source_uri=source_uri,
            collector_id=collector_id,
            bridge_kg=bridge_kg,
        )
        return result.to_dict()

    def get_evidence(self, evidence_id: str) -> dict[str, Any]:
        record = get_eccf_repository().get(evidence_id)
        if record is None:
            return {"ok": False, "error": "evidence_not_found"}
        return {"ok": True, "record": record.to_dict()}

    def verify_integrity(self, evidence_id: str) -> dict[str, Any]:
        record = get_eccf_repository().get(evidence_id)
        if record is None:
            return {"ok": False, "error": "evidence_not_found"}
        result = verify_integrity(
            content_hash=record.content_hash,
            size_bytes=record.size_bytes,
            mime_type=record.mime_type,
            payload=record.payload,
            entity_type=record.entity_type,
            entity_value=record.entity_value,
            source_type=record.source_type,
        )
        return {"ok": result["ok"], "evidence_id": evidence_id, **result}

    def get_audit_trail(self, evidence_id: str) -> dict[str, Any]:
        entries = get_audit_trail().get_trail(evidence_id)
        return {
            "ok": True,
            "evidence_id": evidence_id,
            "count": len(entries),
            "entries": [e.to_dict() for e in entries],
        }

    def get_timeline(self, evidence_id: str) -> dict[str, Any]:
        events = get_evidence_timeline().get_timeline(evidence_id)
        return {
            "ok": True,
            "evidence_id": evidence_id,
            "count": len(events),
            "events": [e.to_dict() for e in events],
        }

    def archive(self, evidence_id: str, *, actor: str = "eccf.api", reason: str | None = None) -> dict[str, Any]:
        result = archive_evidence(evidence_id, actor=actor, reason=reason)
        if result.get("ok"):
            get_eccf_metrics().record_archive()
        return result

    def record_report_usage(self, evidence_id: str, report_id: str, analyst: str) -> dict[str, Any]:
        result = record_report_usage(evidence_id, report_id, analyst)
        if result.get("ok"):
            get_eccf_metrics().record_report_usage()
        return result

    def monitoring(self) -> dict[str, Any]:
        return {"ok": True, **get_eccf_metrics().get_metrics()}

    def search_archive(
        self,
        *,
        case_ref: str | None = None,
        category: str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        results = search_archive(case_ref=case_ref, category=category, query=query)
        return {"ok": True, "count": len(results), "results": results}

    def create_version(
        self,
        evidence_id: str,
        *,
        collector_payload: dict[str, Any] | None = None,
        actor: str = "eccf.api",
    ) -> dict[str, Any]:
        new_rec, diff = create_new_version(evidence_id, collector_payload=collector_payload, actor=actor)
        return {"ok": True, "record": new_rec.to_dict(), "metadata_diff": diff}


_service: ECCFService | None = None


def get_eccf_service() -> ECCFService:
    global _service
    if _service is None:
        _service = ECCFService()
    return _service
