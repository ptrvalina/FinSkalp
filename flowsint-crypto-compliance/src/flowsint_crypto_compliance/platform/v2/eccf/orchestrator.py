"""RFC-0017 Ch.1 — ECCF pipeline orchestrator."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.eccf.audit_trail import AuditAction, get_audit_trail
from flowsint_crypto_compliance.platform.v2.eccf.constraints import eccf_architectural_constraints
from flowsint_crypto_compliance.platform.v2.eccf.generator import generate_evidence
from flowsint_crypto_compliance.platform.v2.eccf.graph_bridge import link_evidence_to_entities
from flowsint_crypto_compliance.platform.v2.eccf.integrity import verify_integrity
from flowsint_crypto_compliance.platform.v2.eccf.monitoring import LatencyTimer, get_eccf_metrics
from flowsint_crypto_compliance.platform.v2.eccf.provenance import build_provenance
from flowsint_crypto_compliance.platform.v2.eccf.repository import get_eccf_repository
from flowsint_crypto_compliance.platform.v2.eccf.timeline import get_evidence_timeline
from flowsint_crypto_compliance.platform.v2.eccf.types import ECCFPipelineResult, ECCFStage, EvidenceLifecycle


async def run_eccf_pipeline(
    *,
    tenant_id: uuid.UUID,
    collector_payload: dict[str, Any],
    case_ref: str | None = None,
    actor: str = "eccf.orchestrator",
    source_uri: str | None = None,
    collector_id: str | None = None,
    bridge_kg: bool = True,
    relation_to: str | None = None,
    relation_type: str | None = None,
) -> ECCFPipelineResult:
    """
    Full ECCF lifecycle: Source → Collector → Evidence Generator → Repository
    → Integrity → KG → Timeline → Report (deferred) → Archive (deferred).
    """
    constraints = eccf_architectural_constraints()
    result = ECCFPipelineResult(ok=True)
    stages: list[str] = []
    metrics = get_eccf_metrics()
    audit = get_audit_trail()
    timeline = get_evidence_timeline()
    repo = get_eccf_repository()

    with LatencyTimer() as timer:
        try:
            # Stage 1: Source validation
            source_type = str(collector_payload.get("source_type") or "osint")
            entity_value = str(collector_payload.get("entity_value") or "")
            if not entity_value:
                raise ValueError("collector_payload.entity_value is required")
            stages.append(ECCFStage.SOURCE.value)
            result.explain["source_type"] = source_type

            # Stage 2: Collector
            stages.append(ECCFStage.COLLECTOR.value)
            result.explain["collector_id"] = collector_id

            # Stage 3: Evidence Generator
            record = generate_evidence(
                tenant_id=tenant_id,
                collector_payload=collector_payload,
                case_ref=case_ref,
                actor=actor,
            )
            stages.append(ECCFStage.EVIDENCE_GENERATOR.value)
            audit.append(record.evidence_id, AuditAction.CREATED, actor=actor)
            audit.append(
                record.evidence_id,
                AuditAction.HASH_CALCULATED,
                actor=actor,
                details={"content_hash": record.content_hash},
            )

            # Stage 4: Repository (dedup by hash)
            stored, deduplicated = repo.store(record, bridge_kg=bridge_kg)
            result.deduplicated = deduplicated
            stages.append(ECCFStage.REPOSITORY.value)

            # Provenance (Ch.9)
            stored.provenance = build_provenance(
                stored,
                collector_id=collector_id,
                source_uri=source_uri,
                actor=actor,
            )

            # Stage 5: Integrity
            integrity = verify_integrity(
                content_hash=stored.content_hash,
                size_bytes=stored.size_bytes,
                mime_type=stored.mime_type,
                payload=stored.payload,
                entity_type=stored.entity_type,
                entity_value=stored.entity_value,
                source_type=stored.source_type,
            )
            result.integrity_ok = integrity["ok"]
            stages.append(ECCFStage.INTEGRITY.value)
            if integrity["ok"]:
                audit.append(stored.evidence_id, AuditAction.VALIDATED, actor=actor)
                repo.update_metadata_only(stored.evidence_id, lifecycle=EvidenceLifecycle.VALIDATED)
            else:
                result.errors.extend(integrity["errors"])

            # Stage 6: Knowledge Graph (via ingest — no direct mutation)
            kg_result: dict[str, Any] = {}
            if bridge_kg and not deduplicated:
                kg_result = link_evidence_to_entities(
                    stored,
                    tenant_id=tenant_id,
                    actor=actor,
                    relation_to=relation_to,
                    relation_type=relation_type,
                )
                result.kg_linked = kg_result.get("ok", False)
                if result.kg_linked:
                    audit.append(
                        stored.evidence_id,
                        AuditAction.LINKED,
                        actor=actor,
                        details=kg_result,
                    )
                    repo.update_metadata_only(stored.evidence_id, lifecycle=EvidenceLifecycle.LINKED)
            stages.append(ECCFStage.KNOWLEDGE_GRAPH.value)
            result.explain["kg"] = kg_result

            # Stage 7: Timeline
            timeline.add_event(
                stored.evidence_id,
                "registered",
                "Evidence registered via ECCF pipeline",
                actor=actor,
                metadata={"case_ref": case_ref, "deduplicated": deduplicated},
            )
            stages.append(ECCFStage.TIMELINE.value)

            # Stage 8: Report (deferred — via report_bridge)
            stages.append(ECCFStage.REPORT.value)
            result.explain["report"] = "deferred_to_report_bridge"

            # Stage 9: Archive (deferred — explicit archive action)
            stages.append(ECCFStage.ARCHIVE.value)
            result.explain["archive"] = "deferred_to_archive_action"

            result.evidence_id = stored.evidence_id
            result.record = stored.to_dict()
            result.stages = stages
            result.explain["constraints"] = constraints
            result.explain["provenance"] = stored.provenance

            metrics.record_registration(
                category=stored.category.value,
                latency_ms=timer.elapsed_ms,
                deduplicated=deduplicated,
                integrity_ok=result.integrity_ok,
                kg_linked=result.kg_linked,
                ok=result.ok,
            )

        except Exception as exc:
            result.ok = False
            result.errors.append(str(exc))
            result.stages = stages
            metrics.record_registration(
                category="unknown",
                latency_ms=timer.elapsed_ms,
                ok=False,
            )

    return result
