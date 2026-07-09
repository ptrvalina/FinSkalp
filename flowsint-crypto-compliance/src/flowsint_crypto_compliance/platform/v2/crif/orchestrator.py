"""RFC-0015 Ch.1 — CRIF pipeline orchestrator."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors import get_connector_registry
from flowsint_crypto_compliance.platform.v2.crif.change_history import get_change_history_store
from flowsint_crypto_compliance.platform.v2.crif.compliance_checks import run_organization_checks
from flowsint_crypto_compliance.platform.v2.crif.connector import RegistryConnector
from flowsint_crypto_compliance.platform.v2.crif.evidence import get_evidence_generator
from flowsint_crypto_compliance.platform.v2.crif.entity_resolver import get_entity_resolver
from flowsint_crypto_compliance.platform.v2.crif.fusion_bridge import run_fusion_bridge
from flowsint_crypto_compliance.platform.v2.crif.jurisdiction import resolve_jurisdiction
from flowsint_crypto_compliance.platform.v2.crif.kg_bridge import ingest_records
from flowsint_crypto_compliance.platform.v2.crif.metrics import get_crif_metrics
from flowsint_crypto_compliance.platform.v2.crif.monitor import get_registry_monitor
from flowsint_crypto_compliance.platform.v2.crif.registry_catalog import (
    get_connector_category,
    register_crif_registry_connectors,
)
from flowsint_crypto_compliance.platform.v2.crif.risk_bridge import emit_risk_compliance_events
from flowsint_crypto_compliance.platform.v2.crif.types import CRIFPipelineResult, CRIFStage
from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus
from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent


def _emit_workspace_events(
    *,
    tenant_id: uuid.UUID,
    case_ref: str | None,
    evidence: list[dict[str, Any]],
    connector_id: str,
) -> int:
    """Investigation workspace stage — emit events only, no direct mutation."""
    bus = get_platform_event_bus()
    count = 0
    for ev in evidence[:5]:
        bus.publish(
            PlatformEvent(
                event_type=EventType.EVIDENCE_CREATED,
                source=f"crif.workspace.{connector_id}",
                tenant_id=tenant_id,
                correlation_id=case_ref,
                payload={
                    "case_ref": case_ref,
                    "evidence_id": ev.get("id"),
                    "entity_type": ev.get("entity_type"),
                    "entity_value": ev.get("entity_value"),
                    "stage": "investigation_workspace",
                    "workspace_mutation": False,
                },
            )
        )
        count += 1
    return count


async def run_crif_pipeline(
    *,
    connector_id: str,
    tenant_id: uuid.UUID,
    query: dict[str, Any] | None = None,
    case_ref: str | None = None,
    organization_key: str | None = None,
    publish: bool = True,
) -> CRIFPipelineResult:
    """
    Main CRIF entry — wires all stages explicitly.
    RegistryConnector MUST NOT mutate graph/risk/investigation; bridges handle downstream.
    """
    register_crif_registry_connectors()
    started = time.perf_counter()
    metrics = get_crif_metrics()
    org_key = organization_key or str((query or {}).get("entity_value") or (query or {}).get("organization") or "")
    result = CRIFPipelineResult(ok=True, connector_id=connector_id, source_category="unknown", organization_key=org_key or None)
    stages: list[str] = []

    try:
        registry = get_connector_registry()
        descriptor = registry.get_descriptor(connector_id)
        if not descriptor:
            raise ValueError(f"Unknown connector: {connector_id}")

        source_cat = get_connector_category(connector_id)
        result.source_category = source_cat.value
        stages.append(CRIFStage.REGISTRY_SOURCE.value)
        result.explain["registry_source"] = {"category": source_cat.value, "connector_id": connector_id}

        connector = registry.create(connector_id)
        reg_connector = RegistryConnector(connector)
        stages.append(CRIFStage.REGISTRY_CONNECTOR.value)

        await reg_connector.connect()
        await reg_connector.authenticate()
        raw = await reg_connector.collect(query=query)
        result.records = raw

        normalized = reg_connector.normalize(raw)
        stages.append(CRIFStage.NORMALIZER.value)
        normalized = resolve_jurisdiction(normalized)
        result.normalized = normalized

        valid, val_errors = reg_connector.validate(normalized)
        stages.append(CRIFStage.SCHEMA_VALIDATOR.value)
        result.errors.extend(val_errors)

        resolved = get_entity_resolver().resolve_records(valid, tenant_id=tenant_id)
        stages.append(CRIFStage.ENTITY_RESOLVER.value)
        result.resolved_entities = resolved

        evidence = get_evidence_generator().generate(
            valid,
            tenant_id=tenant_id,
            connector_id=connector_id,
            case_ref=case_ref,
        )
        stages.append(CRIFStage.EVIDENCE_GENERATOR.value)
        result.evidence = evidence

        if org_key:
            checks = run_organization_checks(valid, organization_key=org_key)
            result.compliance_checks = checks
            get_change_history_store().record_from_records(org_key, valid, source=connector_id)

        record_hash = hashlib.sha256(json.dumps(valid, sort_keys=True, default=str).encode()).hexdigest()
        if org_key:
            change = get_registry_monitor().record_snapshot(connector_id, org_key, record_hash)
            result.explain["monitor"] = change

        fusion_events = 0
        kg_ingested = 0
        risk_events = 0
        workspace_events = 0

        if publish and valid:
            fusion_result = await run_fusion_bridge(
                valid,
                tenant_id=tenant_id,
                case_ref=case_ref,
            )
            result.explain["fusion"] = fusion_result
            fusion_events = fusion_result.get("events_emitted", 0)

            kg_result = ingest_records(
                valid,
                tenant_id=tenant_id,
                case_ref=case_ref,
                actor=f"crif.{connector_id}",
            )
            stages.append(CRIFStage.KNOWLEDGE_GRAPH.value)
            kg_ingested = kg_result.get("ingested", 0)
            result.explain["knowledge_graph"] = kg_result
            if kg_result.get("errors"):
                result.errors.extend(kg_result["errors"])

            risk_result = emit_risk_compliance_events(
                valid,
                tenant_id=tenant_id,
                case_ref=case_ref,
                connector_id=connector_id,
                compliance_checks=result.compliance_checks,
            )
            stages.append(CRIFStage.RISK_ENGINE.value)
            risk_events = risk_result.get("events_emitted", 0)
            result.explain["risk_engine"] = risk_result

            workspace_events = _emit_workspace_events(
                tenant_id=tenant_id,
                case_ref=case_ref,
                evidence=evidence,
                connector_id=connector_id,
            )
            stages.append(CRIFStage.INVESTIGATION_WORKSPACE.value)
            result.explain["investigation_workspace"] = {
                "events_emitted": workspace_events,
                "workspace_mutation": False,
            }

        result.fusion_events = fusion_events
        result.kg_ingested = kg_ingested
        result.risk_events = risk_events
        result.workspace_events = workspace_events

        await reg_connector.shutdown()
        result.ok = bool(valid) or not val_errors

        latency_ms = (time.perf_counter() - started) * 1000
        metrics.record_pipeline(
            connector_id,
            latency_ms=latency_ms,
            success=result.ok,
            records=len(valid),
            checks=len(result.compliance_checks),
            connected=True,
        )
    except Exception as exc:
        result.ok = False
        result.errors.append(str(exc))
        metrics.record_pipeline(connector_id, latency_ms=0, success=False, connected=False)

    result.stages = stages
    return result
