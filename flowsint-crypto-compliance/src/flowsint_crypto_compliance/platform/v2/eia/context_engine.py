"""RFC-0018 Ch.4 — investigation context builder (read-only)."""

from __future__ import annotations

import uuid
from typing import Any

_context_cache: dict[str, dict[str, Any]] = {}


def _cache_key(case_ref: str, entity_keys: list[str]) -> str:
    return f"{case_ref}::{','.join(sorted(entity_keys))}"


def get_cached_context(case_ref: str, entity_keys: list[str]) -> dict[str, Any] | None:
    return _context_cache.get(_cache_key(case_ref, entity_keys))


def set_cached_context(case_ref: str, entity_keys: list[str], context: dict[str, Any]) -> None:
    _context_cache[_cache_key(case_ref, entity_keys)] = context


def reset_context_cache() -> None:
    global _context_cache
    _context_cache = {}


async def build_investigation_context(
    *,
    case_ref: str,
    entity_keys: list[str],
    tenant_id: uuid.UUID | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    Pull multi-source read-only context: case, KG neighbors, timeline,
    evidence, RDE assess, analyst history stub.
    """
    if use_cache:
        cached = get_cached_context(case_ref, entity_keys)
        if cached is not None:
            cached["cache_hit"] = True
            return cached

    from flowsint_crypto_compliance.platform.v2.gateway import (
        case_timeline,
        get_workflow_state,
        list_case_evidence,
    )

    tenant_raw = tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000001")

    # Case / workflow state
    workflow = get_workflow_state(case_ref)
    case_info = {
        "case_ref": case_ref,
        "workflow_stage": workflow.get("stage") or workflow.get("workflow_stage") or "unknown",
        "entity_count": workflow.get("entity_count", 0),
    }

    # Timeline
    timeline_result = case_timeline(case_ref, limit=50)
    timeline_events = timeline_result.get("events") or timeline_result.get("items") or []

    # Evidence (ECCF + case evidence)
    evidence_result = list_case_evidence(case_ref=case_ref)
    evidence_items = evidence_result.get("items") or evidence_result.get("evidence") or []

    # ECCF repository evidence
    eccf_evidence: list[dict[str, Any]] = []
    try:
        from flowsint_crypto_compliance.platform.v2.eccf.repository import get_eccf_repository

        for rec in get_eccf_repository().list_all():
            if rec.case_ref == case_ref:
                eccf_evidence.append(rec.to_dict())
    except Exception:
        pass

    all_evidence = list(evidence_items) + eccf_evidence

    # KG neighbors per entity
    neighbors_by_entity: dict[str, list[dict[str, Any]]] = {}
    for entity_key in entity_keys:
        neighbors_by_entity[entity_key] = _fetch_neighbors(entity_key, tenant_raw)

    # RDE assessment per entity (read-only)
    rde_assessments: dict[str, dict[str, Any]] = {}
    for entity_key in entity_keys:
        rde_assessments[entity_key] = await _fetch_rde_assessment(
            entity_key=entity_key,
            tenant_id=tenant_raw,
            case_ref=case_ref,
        )

    # Analyst history stub
    analyst_history = _fetch_analyst_history_stub(case_ref)

    # Hypotheses stub from intelligence engine patterns
    hypotheses = _fetch_hypotheses_stub(case_ref, entity_keys)

    # Workflow recommendations
    workflow_recs: list[dict[str, Any]] = []
    try:
        from flowsint_crypto_compliance.platform.v2.workflow.recommendations import build_recommendations

        risk_score = None
        if rde_assessments:
            first = next(iter(rde_assessments.values()), {})
            risk_score = (first.get("risk_mapping") or {}).get("score")
        workflow_recs = build_recommendations(
            case_ref=case_ref,
            workflow_stage=case_info["workflow_stage"],
            risk_score=risk_score,
            entity_count=len(entity_keys),
            evidence_count=len(all_evidence),
            hypotheses=hypotheses,
        )
    except Exception:
        pass

    context = {
        "ok": True,
        "case_ref": case_ref,
        "entity_keys": entity_keys,
        "case": case_info,
        "timeline": timeline_events,
        "evidence": all_evidence,
        "evidence_count": len(all_evidence),
        "neighbors": neighbors_by_entity,
        "rde_assessments": rde_assessments,
        "analyst_history": analyst_history,
        "hypotheses": hypotheses,
        "workflow_recommendations": workflow_recs,
        "cache_hit": False,
        "sources": _list_sources(case_info, all_evidence, neighbors_by_entity, rde_assessments),
    }

    set_cached_context(case_ref, entity_keys, context)
    return context


def _fetch_neighbors(entity_key: str, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    try:
        from flowsint_crypto_compliance.platform.v2.knowledge_store import get_knowledge_graph_store

        store = get_knowledge_graph_store()
        entities = store.list_entities(tenant_id=tenant_id)
        for ent in entities:
            if ent.canonical_key == entity_key:
                neighbors = store.get_neighbors(ent.id, direction="both")
                return [
                    {
                        **nb,
                        "canonical_key": (nb.get("entity") or {}).get("canonical_key"),
                        "rel_type": nb.get("relation_type"),
                    }
                    for nb in neighbors
                ]
    except Exception:
        pass
    return []


async def _fetch_rde_assessment(
    *,
    entity_key: str,
    tenant_id: uuid.UUID,
    case_ref: str,
) -> dict[str, Any]:
    try:
        from flowsint_crypto_compliance.platform.v2.rde.orchestrator import run_rde_assessment

        result = await run_rde_assessment(
            entity_key=entity_key,
            tenant_id=tenant_id,
            case_ref=case_ref,
        )
        return result.to_dict() if hasattr(result, "to_dict") else {"ok": result.ok}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _fetch_analyst_history_stub(case_ref: str) -> dict[str, Any]:
    """Stub — analyst workspace history (RFC-0010)."""
    return {
        "case_ref": case_ref,
        "recent_actions": [],
        "comments_count": 0,
        "last_activity": None,
        "stub": True,
    }


def _fetch_hypotheses_stub(case_ref: str, entity_keys: list[str]) -> list[dict[str, Any]]:
    try:
        from flowsint_crypto_compliance.platform.v2.intelligence_engine.hypotheses import generate_hypotheses
        from flowsint_crypto_compliance.platform.v2.intelligence_engine.types import (
            IntelligenceEngineContext,
            PatternHit,
        )

        ctx = IntelligenceEngineContext(case_ref=case_ref, address=entity_keys[0] if entity_keys else None)
        patterns = [PatternHit(code="SHARED_IP", confidence=0.6, explain={})]
        hyps = generate_hypotheses(ctx, patterns)
        return [
            {
                "id": h.code,
                "statement_ru": h.statement_ru,
                "confidence": h.confidence,
                "explain": h.explain,
            }
            for h in hyps
        ]
    except Exception:
        return []


def _list_sources(
    case_info: dict[str, Any],
    evidence: list[dict[str, Any]],
    neighbors: dict[str, list],
    rde: dict[str, dict],
) -> list[str]:
    sources = ["workflow", "timeline"]
    if evidence:
        sources.append("evidence")
    if any(neighbors.values()):
        sources.append("knowledge_graph")
    if any(r.get("ok") for r in rde.values()):
        sources.append("rde")
    return sources
