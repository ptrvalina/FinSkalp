"""Platform v2 gateway handlers — shared by flowsint-api and demo BFF (RFC-0002 M3)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from flowsint_crypto_compliance.platform.v2.events import SCHEMA_VERSION
from flowsint_crypto_compliance.platform.v2.plugin_registry import get_plugin_registry


def architecture_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0002",
        "rfc_extensions": ["RFC-0003", "RFC-0004", "RFC-0005", "RFC-0006", "RFC-0007", "RFC-0008", "RFC-0009", "RFC-0010", "RFC-0011", "RFC-0012", "RFC-0013", "RFC-0014", "RFC-0015", "RFC-0016", "RFC-0017"],
        "schema_version": SCHEMA_VERSION,
        "knowledge_model": "RFC-0003",
        "layers": [
            "acquisition",
            "fusion",
            "knowledge",
            "analytics",
            "investigation",
            "presentation",
        ],
        "core_components": [
            "Intelligence Fusion Engine",
            "Knowledge Graph",
            "Entity Resolution Engine",
            "Evidence Center",
            "Investigation Workspace",
        ],
        "rfc0003_components": [
            "Unified Data Model",
            "Knowledge Graph v2.0",
            "Confidence Model",
            "Graph History",
            "Mandatory Ingest Pipeline",
        ],
        "plugins": get_plugin_registry().manifest(),
        "docs": "/docs/architecture/v2/README.md",
        "rfc0003_docs": "/docs/rfc/RFC-0003-unified-data-model-knowledge-graph.md",
        "rfc0004_docs": "/docs/rfc/RFC-0004-intelligence-platform.md",
        "rfc0005_docs": "/docs/rfc/RFC-0005-investigation-platform.md",
        "intelligence_manifest": "/api/platform/v2/intelligence/manifest",
        "investigation_manifest": "/api/platform/v2/investigation/manifest",
        "intelligence_engine_manifest": "/api/platform/v2/intelligence-engine/manifest",
        "connectors_manifest": "/api/platform/v2/connectors/manifest",
        "design_system_manifest": "/api/platform/v2/design-system/manifest",
        "rbac_manifest": "/api/platform/v2/rbac/manifest",
        "analyst_workspace_manifest": "/api/platform/v2/analyst-workspace/manifest",
        "workflow_manifest": "/api/platform/v2/workflow/manifest",
        "blockchain_intelligence_manifest": "/api/platform/v2/blockchain-intelligence/manifest",
        "blockchain_sync_status": "/api/platform/v2/blockchain-intelligence/sync/status",
        "icf_manifest": "/api/platform/v2/icf/manifest",
        "crif_manifest": "/api/platform/v2/crif/manifest",
        "rde_manifest": "/api/platform/v2/rde/manifest",
        "eccf_manifest": "/api/platform/v2/eccf/manifest",
    }


def get_intelligence_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.intelligence import get_intelligence_orchestrator

    return get_intelligence_orchestrator().manifest()


def run_intelligence(
    *,
    tenant_id: uuid.UUID,
    address: str | None = None,
    chain: str | None = None,
    case_ref: str | None = None,
    investigation_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    screening: dict[str, Any] | None = None,
    attribution: dict[str, Any] | None = None,
    mentions: list[dict[str, Any]] | None = None,
    publish: bool = True,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.intelligence import run_intelligence_analysis

    result = run_intelligence_analysis(
        tenant_id=tenant_id,
        address=address,
        chain=chain,
        case_ref=case_ref,
        investigation_id=investigation_id,
        entity_id=entity_id,
        screening=screening,
        attribution=attribution,
        mentions=mentions,
        publish=publish,
    )
    return result.to_dict()


def get_intelligence_engine_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.intelligence_engine import get_intelligence_engine_orchestrator

    return get_intelligence_engine_orchestrator().manifest()


def run_intelligence_engine(
    *,
    tenant_id: uuid.UUID,
    address: str | None = None,
    chain: str | None = None,
    case_ref: str | None = None,
    investigation_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    screening: dict[str, Any] | None = None,
    attribution: dict[str, Any] | None = None,
    mentions: list[dict[str, Any]] | None = None,
    publish: bool = True,
    learn_memory: bool = True,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.intelligence_engine import run_intelligence_engine as _run

    result = _run(
        tenant_id=tenant_id,
        address=address,
        chain=chain,
        case_ref=case_ref,
        investigation_id=investigation_id,
        entity_id=entity_id,
        screening=screening,
        attribution=attribution,
        mentions=mentions,
        publish=publish,
        learn_memory=learn_memory,
    )
    return result.to_dict()


def case_timeline(case_ref: str, *, limit: int = 100) -> dict[str, Any]:
    """CQRS read model from finskalp_platform_events."""
    try:
        from flowsint_core.core.postgre_db import SessionLocal
        from flowsint_crypto_compliance.storage.db_models import FinskalpPlatformEvent
    except Exception:
        return {"case_ref": case_ref, "events": [], "source": "unavailable"}

    db = SessionLocal()
    try:
        rows = (
            db.query(FinskalpPlatformEvent)
            .filter(FinskalpPlatformEvent.payload.contains({"case_ref": case_ref}))
            .order_by(FinskalpPlatformEvent.occurred_at.desc())
            .limit(limit)
            .all()
        )
        events = [
            {
                "id": str(r.id),
                "event_type": r.event_type,
                "occurred_at": r.occurred_at.isoformat() if isinstance(r.occurred_at, datetime) else str(r.occurred_at),
                "source": r.source,
                "actor": r.actor,
                "investigation_id": str(r.investigation_id) if r.investigation_id else None,
                "payload": r.payload,
            }
            for r in rows
        ]
        return {"case_ref": case_ref, "events": events, "count": len(events), "source": "finskalp_platform_events"}
    except Exception:
        return {"case_ref": case_ref, "events": [], "source": "error"}
    finally:
        db.close()


def get_investigation_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.investigation_platform import investigation_platform_manifest

    return investigation_platform_manifest()


def get_operations_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.investigation_platform import operations_manifest

    return operations_manifest()


def get_investigation_workspace(case_ref: str, *, case: Any | None = None) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.investigation_platform import get_investigation_platform_service

    return get_investigation_platform_service().get_workspace(case_ref, case=case)


def list_case_evidence(
    *,
    case_ref: str,
    case_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.investigation_platform import get_investigation_platform_service

    return get_investigation_platform_service().list_evidence(case_ref=case_ref, case_id=case_id)


def register_case_evidence(
    *,
    case_ref: str,
    source_type: str,
    entity_type: str,
    entity_value: str,
    actor: str,
    acquisition_method: str = "manual_upload",
    payload: dict[str, Any] | None = None,
    case_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.investigation_platform import get_investigation_platform_service

    return get_investigation_platform_service().register_evidence(
        case_ref=case_ref,
        source_type=source_type,
        entity_type=entity_type,
        entity_value=entity_value,
        actor=actor,
        acquisition_method=acquisition_method,
        payload=payload,
        case_id=case_id,
    )


def update_evidence_status(
    evidence_id: uuid.UUID,
    *,
    new_status: str,
    actor: str,
    reason: str | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.investigation_platform import get_investigation_platform_service

    return get_investigation_platform_service().update_evidence_status(
        evidence_id,
        new_status=new_status,
        actor=actor,
        reason=reason,
    )


def explain_investigation_entity(case_ref: str, entity_id: uuid.UUID) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.investigation_platform import get_investigation_platform_service

    return get_investigation_platform_service().explain_object(case_ref, entity_id)


def list_plugins() -> list[dict[str, Any]]:
    return get_plugin_registry().manifest()


def get_connectors_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.connectors import (
        get_connector_registry,
        integration_security_manifest,
        sdk_manifest,
    )

    m = get_connector_registry().manifest()
    m["sdk"] = sdk_manifest()
    m["security"] = integration_security_manifest()
    return m


def get_design_system_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.design_system import design_system_manifest

    return design_system_manifest()


def get_rbac_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.rbac import harmonized_manifest

    return harmonized_manifest()


def get_rbac_effective(
    db: Any,
    user_id: uuid.UUID,
    *,
    investigation_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.rbac.harmonization import resolve_effective_permissions

    return resolve_effective_permissions(db, user_id, investigation_id=investigation_id)


def get_workflow_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.workflow import workflow_manifest

    return workflow_manifest()


def get_workflow_state(case_ref: str | None = None) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.workflow import get_workflow_orchestrator

    return get_workflow_orchestrator().get_workflow_state(case_ref=case_ref)


def get_workflow_recommendations(case_ref: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.workflow import get_workflow_orchestrator

    return get_workflow_orchestrator().get_recommendations(case_ref=case_ref)


def get_workflow_first_login() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.workflow import get_workflow_orchestrator

    return get_workflow_orchestrator().get_first_login_briefing()


async def start_workflow_investigation(
    *,
    case_ref: str,
    seed_type: str,
    seed_value: str,
    chain: str = "tron",
    investigation_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.workflow import get_workflow_orchestrator

    return await get_workflow_orchestrator().start_workflow(
        case_ref=case_ref,
        seed_type=seed_type,
        seed_value=seed_value,
        chain=chain,
        investigation_id=investigation_id,
    )


def get_workflow_recovery(user_id: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.workflow.recovery import get_recovery_state

    return get_recovery_state(user_id)


def save_workflow_recovery(user_id: str, state: dict[str, Any]) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.workflow.recovery import save_recovery_state

    return save_recovery_state(user_id, state)


def get_blockchain_intelligence_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.blockchain_intelligence import blockchain_intelligence_manifest

    return blockchain_intelligence_manifest()


async def analyze_blockchain_address(
    *,
    address: str,
    chain: str,
    case_ref: str | None = None,
    tenant_id: uuid.UUID | None = None,
    publish: bool = True,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.blockchain_intelligence import get_blockchain_intelligence_service

    return await get_blockchain_intelligence_service().analyze_address(
        address=address,
        chain=chain,
        case_ref=case_ref,
        tenant_id=tenant_id,
        publish=publish,
    )


async def run_blockchain_sync(chains: list[str] | None = None, *, simulate: bool | None = None) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.block_sync import (
        sync_all_chains,
        sync_chain_incremental,
    )

    if chains:
        results = []
        for ch in chains:
            results.append(await sync_chain_incremental(ch, simulate=bool(simulate)))
        from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.sync_store import get_block_sync_store

        return {"ok": True, "results": results, "status": get_block_sync_store().status()}
    return await sync_all_chains(simulate=simulate)


def get_blockchain_sync_status() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.sync_store import get_block_sync_store

    return {"ok": True, **get_block_sync_store().status()}


def get_analyst_workspace_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.analyst_workspace import analyst_workspace_manifest

    return analyst_workspace_manifest()


def get_analyst_workspace_state(
    *,
    case_ref: str | None = None,
    investigation_id: uuid.UUID | str | None = None,
    case: Any | None = None,
    user_id: str = "default",
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.analyst_workspace import get_workspace_state_timed

    return get_workspace_state_timed(
        case_ref=case_ref,
        investigation_id=investigation_id,
        case=case,
        user_id=user_id,
    )


def analyst_workspace_search(
    query: str,
    *,
    tenant_id: uuid.UUID | None = None,
    case_ref: str | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.analyst_workspace import universal_search, with_latency_ms

    return with_latency_ms(
        universal_search,
        query,
        tenant_id,
        case_ref=case_ref,
    )


def analyst_workspace_add_comment(
    *,
    case_ref: str,
    text: str,
    author: str = "analyst",
    tenant_id: str | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.analyst_workspace import add_comment, with_latency_ms

    return with_latency_ms(
        add_comment,
        case_ref=case_ref,
        text=text,
        author=author,
        tenant_id=tenant_id,
    )


def analyst_workspace_collaboration_activity(case_ref: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.analyst_workspace import get_collaboration_activity, with_latency_ms

    return with_latency_ms(get_collaboration_activity, case_ref)


def analyst_workspace_get_personalization(user_id: str = "default") -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.analyst_workspace import get_personalization, with_latency_ms

    return with_latency_ms(get_personalization, user_id)


def analyst_workspace_save_personalization(user_id: str, preferences: dict[str, Any]) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.analyst_workspace import save_personalization, with_latency_ms

    return with_latency_ms(save_personalization, user_id, preferences)


async def run_connector_collect(
    connector_id: str,
    *,
    tenant_id: uuid.UUID,
    query: dict[str, Any] | None = None,
    case_ref: str | None = None,
    publish: bool = True,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.connectors import get_connector_registry

    connector = get_connector_registry().create(connector_id)
    result = await connector.run_pipeline(
        query=query,
        tenant_id=tenant_id,
        case_ref=case_ref,
        publish=publish,
    )
    return result.to_dict()


async def connector_health(connector_id: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.connectors import get_connector_registry

    connector = get_connector_registry().create(connector_id)
    await connector.connect()
    await connector.authenticate()
    health = await connector.health()
    await connector.shutdown()
    return {"connector_id": connector_id, **health}


def get_icf_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.icf import get_icf_service

    return get_icf_service().manifest()


async def run_icf_collect(
    *,
    connector_id: str,
    tenant_id: uuid.UUID,
    query: dict[str, Any] | None = None,
    case_ref: str | None = None,
    publish: bool = True,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.icf import get_icf_service

    return await get_icf_service().collect(
        connector_id=connector_id,
        tenant_id=tenant_id,
        query=query,
        case_ref=case_ref,
        publish=publish,
    )


def get_icf_scheduler_status() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.icf import get_icf_service

    return get_icf_service().scheduler_status()


def schedule_icf_job(
    *,
    connector_id: str,
    query: dict[str, Any] | None = None,
    case_ref: str | None = None,
    tenant_id: str | None = None,
    interval_seconds: int = 300,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.icf import get_icf_service

    return get_icf_service().schedule_job(
        connector_id=connector_id,
        query=query,
        case_ref=case_ref,
        tenant_id=tenant_id,
        interval_seconds=interval_seconds,
    )


def get_icf_monitoring(connector_id: str | None = None) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.icf import get_icf_service

    return get_icf_service().monitoring(connector_id)


def get_crif_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.crif import get_crif_service

    return get_crif_service().manifest()


async def run_crif_check(
    *,
    connector_id: str,
    tenant_id: uuid.UUID,
    query: dict[str, Any] | None = None,
    case_ref: str | None = None,
    organization_key: str | None = None,
    publish: bool = True,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.crif import get_crif_service

    return await get_crif_service().check(
        connector_id=connector_id,
        tenant_id=tenant_id,
        query=query,
        case_ref=case_ref,
        organization_key=organization_key,
        publish=publish,
    )


def run_crif_sanctions_screen(name: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.crif import get_crif_service

    return get_crif_service().screen_sanctions(name)


def get_crif_rules() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.crif import get_crif_service

    return get_crif_service().get_rules()


def evaluate_crif_rules(context: dict[str, Any]) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.crif import get_crif_service

    return get_crif_service().evaluate_rules(context)


def get_crif_metrics(connector_id: str | None = None) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.crif import get_crif_service

    return get_crif_service().metrics(connector_id)


def get_crif_change_history(entity_key: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.crif import get_crif_service

    return get_crif_service().change_history(entity_key)


def get_rde_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.rde import get_rde_service

    return get_rde_service().manifest()


async def run_rde_assess(
    *,
    entity_key: str,
    tenant_id: uuid.UUID,
    case_ref: str | None = None,
    signals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.rde import get_rde_service

    return await get_rde_service().assess(
        entity_key=entity_key,
        tenant_id=tenant_id,
        case_ref=case_ref,
        signals=signals,
    )


def get_rde_rules() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.rde import get_rde_service

    return get_rde_service().get_rules()


def evaluate_rde_rules(context: dict[str, Any]) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.rde import get_rde_service

    return get_rde_service().evaluate_rules(context)


def get_rde_monitoring() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.rde import get_rde_service

    return get_rde_service().monitoring()


def get_rde_priorities(case_ref: str | None = None) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.rde import get_rde_service

    return get_rde_service().priorities(case_ref)


def get_eccf_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.eccf import get_eccf_service

    return get_eccf_service().manifest()


async def register_eccf_evidence(
    *,
    tenant_id: uuid.UUID,
    collector_payload: dict[str, Any],
    case_ref: str | None = None,
    actor: str = "eccf.gateway",
    source_uri: str | None = None,
    collector_id: str | None = None,
    bridge_kg: bool = True,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.eccf import get_eccf_service

    return await get_eccf_service().register(
        tenant_id=tenant_id,
        collector_payload=collector_payload,
        case_ref=case_ref,
        actor=actor,
        source_uri=source_uri,
        collector_id=collector_id,
        bridge_kg=bridge_kg,
    )


def get_eccf_evidence(evidence_id: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.eccf import get_eccf_service

    return get_eccf_service().get_evidence(evidence_id)


def verify_eccf_integrity(evidence_id: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.eccf import get_eccf_service

    return get_eccf_service().verify_integrity(evidence_id)


def get_eccf_audit_trail(evidence_id: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.eccf import get_eccf_service

    return get_eccf_service().get_audit_trail(evidence_id)


def get_eccf_timeline(evidence_id: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.eccf import get_eccf_service

    return get_eccf_service().get_timeline(evidence_id)


def archive_eccf_evidence(
    evidence_id: str,
    *,
    actor: str = "eccf.gateway",
    reason: str | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.eccf import get_eccf_service

    return get_eccf_service().archive(evidence_id, actor=actor, reason=reason)


def record_eccf_report_usage(evidence_id: str, report_id: str, analyst: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.eccf import get_eccf_service

    return get_eccf_service().record_report_usage(evidence_id, report_id, analyst)


def get_eccf_monitoring() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.eccf import get_eccf_service

    return get_eccf_service().monitoring()


def emit_scalpel_collect_event(
    *,
    case_ref: str | None,
    tenant_id: uuid.UUID | None,
    investigation_id: uuid.UUID | None,
    mentions: list[dict[str, Any]],
    source: str = "scalpel.collect",
) -> int:
    """Emit OsintMentionFound for each extracted mention."""
    from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
    from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus

    bus = get_platform_event_bus()
    count = 0
    for m in mentions:
        if not isinstance(m, dict):
            continue
        bus.publish(
            PlatformEvent(
                event_type=EventType.OSINT_MENTION_FOUND,
                source=source,
                tenant_id=tenant_id,
                investigation_id=investigation_id,
                payload={
                    "case_ref": case_ref,
                    "entity_type": m.get("entity_type", "domain"),
                    "entity_value": m.get("entity_value") or m.get("url") or m.get("mention"),
                    "source_type": m.get("source_type") or m.get("collector_id") or "scalpel",
                    "confidence": m.get("confidence") or 0.5,
                    **m,
                },
            )
        )
        count += 1
    return count


def get_knowledge_model() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.knowledge_graph import knowledge_model_manifest

    return knowledge_model_manifest()


def get_entity(entity_id: uuid.UUID) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.knowledge_graph import get_knowledge_graph_service

    kg = get_knowledge_graph_service()
    ent = kg.get_entity(entity_id)
    if not ent:
        return {"error": "Сущность не найдена", "entity_id": str(entity_id)}
    return {"entity": ent.model_dump(mode="json")}


def get_entity_neighbors(entity_id: uuid.UUID, *, direction: str = "both") -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.knowledge_graph import get_knowledge_graph_service

    kg = get_knowledge_graph_service()
    if not kg.get_entity(entity_id):
        return {"error": "Сущность не найдена", "entity_id": str(entity_id)}
    neighbors = kg.get_neighbors(entity_id, direction=direction)
    return {"entity_id": str(entity_id), "neighbors": neighbors, "count": len(neighbors)}


def get_entity_history(entity_id: uuid.UUID) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.knowledge_graph import get_knowledge_graph_service

    kg = get_knowledge_graph_service()
    history = kg.get_entity_history(entity_id)
    return {"entity_id": str(entity_id), "history": history, "count": len(history)}


def get_graph_at(tenant_id: uuid.UUID, as_of: datetime) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.knowledge_graph import get_knowledge_graph_service

    kg = get_knowledge_graph_service()
    snap = kg.graph_at(tenant_id, as_of)
    return snap


def get_relation_evidence(relation_id: uuid.UUID) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.knowledge_graph import get_knowledge_graph_service

    kg = get_knowledge_graph_service()
    evidence = kg.get_relation_evidence(relation_id)
    return {
        "relation_id": str(relation_id),
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "count": len(evidence),
    }


def get_relation_history(relation_id: uuid.UUID) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.knowledge_graph import get_knowledge_graph_service

    kg = get_knowledge_graph_service()
    history = kg.get_relation_history(relation_id)
    return {"relation_id": str(relation_id), "history": history, "count": len(history)}


def compare_entity_versions(
    entity_id: uuid.UUID,
    version_a: int,
    version_b: int,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.knowledge_graph import get_knowledge_graph_service

    kg = get_knowledge_graph_service()
    result = kg.compare_entity_versions(entity_id, version_a, version_b)
    if result.get("error"):
        return result
    return result


def export_evidence_base(
    tenant_id: uuid.UUID,
    *,
    case_ref: str | None = None,
    case_id: uuid.UUID | None = None,
    fmt: str = "json",
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.knowledge_graph import get_knowledge_graph_service

    kg = get_knowledge_graph_service()
    data = kg.export_evidence_base(tenant_id, case_ref=case_ref, case_id=case_id)
    data["format"] = fmt
    return data


def create_graph_snapshot(
    tenant_id: uuid.UUID,
    *,
    actor: str = "api",
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.knowledge_graph import get_knowledge_graph_service

    kg = get_knowledge_graph_service()
    return kg.create_graph_snapshot(tenant_id, changed_by=actor)


def get_pipeline_chain_manifest() -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.pipeline_chain import pipeline_chain_manifest

    return pipeline_chain_manifest()


def ingest_record(
    *,
    tenant_id: uuid.UUID,
    source_type: str,
    entity_type: str,
    entity_value: str,
    payload: dict[str, Any] | None = None,
    actor: str = "api",
    confidence: float = 0.5,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.ingest_pipeline import get_ingest_pipeline

    result = get_ingest_pipeline().ingest(
        tenant_id=tenant_id,
        source_type=source_type,
        entity_type=entity_type,
        entity_value=entity_value,
        payload=payload,
        actor=actor,
        confidence=confidence,
        require_relation_evidence=False,
    )
    return {
        "ok": result.ok,
        "entity_id": str(result.entity_id) if result.entity_id else None,
        "evidence_id": str(result.evidence_id) if result.evidence_id else None,
        "relation_id": str(result.relation_id) if result.relation_id else None,
        "merge_decision": result.merge_decision,
        "confidence": result.confidence,
        "stages_completed": result.stages_completed,
        "errors": result.errors,
        "message": "Данные приняты через обязательный путь ingest" if result.ok else "Ошибка ingest",
    }
