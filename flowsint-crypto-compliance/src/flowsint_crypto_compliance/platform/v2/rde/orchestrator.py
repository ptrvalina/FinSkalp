"""RFC-0016 Ch.1 — RDE pipeline orchestrator."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.rde.aggregator import aggregate_factors
from flowsint_crypto_compliance.platform.v2.rde.confidence import calculate_confidence
from flowsint_crypto_compliance.platform.v2.rde.constraints import rde_architectural_constraints
from flowsint_crypto_compliance.platform.v2.rde.correlator import correlate_signals
from flowsint_crypto_compliance.platform.v2.rde.decision_support import generate_recommendations
from flowsint_crypto_compliance.platform.v2.rde.explainability import build_explanation
from flowsint_crypto_compliance.platform.v2.rde.factors import calculate_all_factors
from flowsint_crypto_compliance.platform.v2.rde.monitoring import LatencyTimer, get_rde_metrics
from flowsint_crypto_compliance.platform.v2.rde.normalizer import normalize_signals
from flowsint_crypto_compliance.platform.v2.rde.prioritization import prioritize_investigation_objects
from flowsint_crypto_compliance.platform.v2.rde.risk_levels import map_score_to_risk_level
from flowsint_crypto_compliance.platform.v2.rde.rules_engine import get_rules_engine
from flowsint_crypto_compliance.platform.v2.rde.temporal import AssessmentSnapshot, get_temporal_store
from flowsint_crypto_compliance.platform.v2.rde.types import RDEAssessmentResult, RDEStage, RiskLevel


async def _acquire_signals(
    *,
    tenant_id: uuid.UUID,
    entity_key: str,
    case_ref: str | None,
    input_signals: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Acquire signals from subsystems via input context dict.
    Read-only — does NOT mutate source data, KG, or evidence.
    """
    signals: dict[str, Any] = dict(input_signals or {})

    if not signals.get("blockchain_signals"):
        try:
            from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.service import (
                get_blockchain_intelligence_service,
            )

            svc = get_blockchain_intelligence_service()
            if hasattr(svc, "get_profile_signals"):
                signals["blockchain_signals"] = svc.get_profile_signals(entity_key)
        except Exception:
            pass

    if not signals.get("registry_signals"):
        signals.setdefault("registry_signals", {})

    if not signals.get("osint_signals"):
        signals.setdefault("osint_signals", {"mentions": []})

    if not signals.get("graph_signals"):
        try:
            from flowsint_crypto_compliance.platform.v2.knowledge_store import get_knowledge_graph_store

            store = get_knowledge_graph_store()
            entities = store.search_entities_by_value(tenant_id, entity_key)
            neighbors: list[dict[str, Any]] = []
            for ent in entities[:3]:
                neighbors.extend(store.get_neighbors(ent.id))
            signals["graph_signals"] = {"neighbors": neighbors, "depth": 1}
        except Exception:
            signals.setdefault("graph_signals", {"neighbors": []})

    if not signals.get("evidence_signals"):
        try:
            from flowsint_crypto_compliance.platform.v2.evidence_center import list_case_evidence_items

            if case_ref:
                items = list_case_evidence_items(case_ref)
                signals["evidence_signals"] = {"items": items}
            else:
                signals.setdefault("evidence_signals", {"items": []})
        except Exception:
            signals.setdefault("evidence_signals", {"items": []})

    return signals


def _build_rule_context(
    signals: dict[str, dict[str, Any]],
    aggregated: dict[str, Any],
    temporal: dict[str, Any],
) -> dict[str, Any]:
    blockchain = signals.get("blockchain") or {}
    registry = signals.get("registry") or {}
    evidence = signals.get("evidence") or {}
    ctx: dict[str, Any] = {
        "activity_spike": temporal.get("spike_detected", False),
        "new_links": len((signals.get("graph") or {}).get("neighbors") or []) > 0,
        "multi_source_evidence": len(evidence.get("items") or []) >= 2 and len(
            [g for g, s in signals.items() if s]
        ) >= 2,
        "sanctioned": bool(registry.get("sanctioned")),
        "mixer_exposure": bool(blockchain.get("mixer_exposure")),
        "org_status": registry.get("org_status"),
        "operations_active": bool(blockchain.get("transaction_count", 0) > 0),
        "composite_score": aggregated.get("composite_score", 0),
    }
    return ctx


async def run_rde_assessment(
    *,
    entity_key: str,
    tenant_id: uuid.UUID,
    case_ref: str | None = None,
    signals: dict[str, Any] | None = None,
) -> RDEAssessmentResult:
    """
    Main RDE entry — full pipeline.
    MUST NOT mutate source data/KG/evidence or make final decisions.
    """
    constraints = rde_architectural_constraints()
    result = RDEAssessmentResult(ok=True, entity_key=entity_key, case_ref=case_ref)
    stages: list[str] = []
    metrics = get_rde_metrics()

    with LatencyTimer() as timer:
        try:
            # Stage 1: Fact acquisition (read-only)
            raw_signals = await _acquire_signals(
                tenant_id=tenant_id,
                entity_key=entity_key,
                case_ref=case_ref,
                input_signals=signals,
            )
            stages.append(RDEStage.FACT_ACQUISITION.value)
            result.explain["acquired_groups"] = list(raw_signals.keys())

            # Stage 2: Normalize
            normalized = normalize_signals(raw_signals)
            stages.append(RDEStage.NORMALIZE.value)

            # Stage 3: Correlate
            correlations = correlate_signals(normalized)
            result.correlations = correlations
            stages.append(RDEStage.CORRELATE.value)

            # Stage 4: Aggregate factors
            factor_results = calculate_all_factors(normalized)
            aggregated = aggregate_factors(factor_results, correlations=correlations)
            result.factor_scores = aggregated["factor_scores"]
            stages.append(RDEStage.AGGREGATE_FACTORS.value)

            # Stage 5: Calculate scores + confidence
            confidence = calculate_confidence(
                normalized, correlations=correlations, factor_results=factor_results
            )
            result.confidence = confidence.to_dict()
            result.composite_score = aggregated["composite_score"]
            stages.append(RDEStage.CALCULATE_SCORES.value)

            # Temporal analysis (in-memory, no source mutation)
            temporal_store = get_temporal_store()
            prev_snaps = temporal_store.get_snapshots(entity_key)
            prev_level = RiskLevel(prev_snaps[-1].risk_level) if prev_snaps else None

            risk_mapping = map_score_to_risk_level(result.composite_score, previous_level=prev_level)
            result.risk_level = RiskLevel(risk_mapping["risk_level"])

            snapshot = AssessmentSnapshot(
                entity_key=entity_key,
                case_ref=case_ref,
                composite_score=result.composite_score,
                risk_level=result.risk_level.value,
                factor_scores=result.factor_scores,
            )
            temporal_store.save_snapshot(snapshot)
            spike = temporal_store.detect_spike(entity_key)
            trends = temporal_store.get_trends(entity_key)
            period_compare = temporal_store.compare_periods(entity_key)
            result.temporal = {"spike": spike, "trends": trends, "period_compare": period_compare}

            # Stage 6: Rule check
            rule_context = _build_rule_context(normalized, aggregated, spike)
            rule_events = get_rules_engine().evaluate(rule_context)
            result.rule_events = [e.to_dict() for e in rule_events]
            stages.append(RDEStage.RULE_CHECK.value)

            # Stage 7: Explain
            result.explain = build_explanation(
                entity_key=entity_key,
                signals=normalized,
                factor_results=factor_results,
                risk_mapping=risk_mapping,
                confidence=result.confidence,
                correlations=correlations,
                rule_events=result.rule_events,
            )
            result.explain["risk_mapping"] = risk_mapping
            result.explain["constraints"] = constraints
            stages.append(RDEStage.EXPLAIN.value)

            # Stage 8: Deliver (recommendations + priorities — NOT decisions)
            result.recommendations = generate_recommendations(
                entity_key=entity_key,
                risk_level=result.risk_level,
                signals=normalized,
                correlations=correlations,
                rule_events=result.rule_events,
            )
            result.priorities = prioritize_investigation_objects(
                entity_key=entity_key,
                case_ref=case_ref,
                factor_scores=result.factor_scores,
                correlations=correlations,
                rule_events=result.rule_events,
                composite_score=result.composite_score,
            )
            stages.append(RDEStage.DELIVER.value)

            result.stages = stages
            metrics.record_assessment(
                entity_key=entity_key,
                risk_level=result.risk_level.value,
                latency_ms=timer.elapsed_ms,
                rule_count=len(result.rule_events),
                ok=True,
            )

        except Exception as exc:
            result.ok = False
            result.errors.append(str(exc))
            result.stages = stages
            metrics.record_assessment(
                entity_key=entity_key,
                risk_level="unknown",
                latency_ms=timer.elapsed_ms,
                ok=False,
            )

    return result
