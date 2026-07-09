"""RFC-0006 Intelligence Score — Ch.9."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.intelligence_engine.types import (
    Hypothesis,
    IntelligenceEngineContext,
    IntelligenceScoreBundle,
    PatternHit,
)


def calculate_intelligence_scores(
    ctx: IntelligenceEngineContext,
    *,
    patterns: list[PatternHit],
    hypotheses: list[Hypothesis],
    evidence_count: int = 0,
    engines_run: int = 0,
    behavior_stability: float = 0.7,
    fusion_trust_avg: float = 0.5,
) -> IntelligenceScoreBundle:
    """Eight independent metrics — no single magic risk score."""
    attribution = ctx.attribution or {}
    screening = ctx.screening or {}
    labels = attribution.get("labels") or {}

    identity = 0.4
    if labels:
        identity = min(0.95, 0.5 + len(labels) * 0.08)
    if attribution.get("entity_id") or ctx.entity_id:
        identity = max(identity, 0.65)

    evidence = min(100.0, evidence_count * 12.0 + len(ctx.mentions) * 3.0)
    if screening.get("evidence_strength"):
        evidence = max(evidence, float(screening["evidence_strength"]))

    relations = min(100.0, len(patterns) * 15.0 + len(ctx.prior_findings) * 5.0)
    if any(p.code.startswith("SHARED") or p.code.startswith("REPEATED") for p in patterns):
        relations = max(relations, 55.0)

    behavior = behavior_stability * 100.0

    source_rel = min(100.0, fusion_trust_avg * 100.0 + len(ctx.mentions) * 2.0)

    completeness = 0.0
    if ctx.case_ref:
        completeness += 20.0
    if ctx.investigation_id:
        completeness += 15.0
    if evidence_count:
        completeness += min(40.0, evidence_count * 8.0)
    if engines_run:
        completeness += min(25.0, engines_run * 2.0)
    completeness = min(100.0, completeness)

    hyp_conf = 0.0
    if hypotheses:
        hyp_conf = sum(h.confidence for h in hypotheses) / len(hypotheses) * 100.0

    progress = min(100.0, completeness * 0.6 + (engines_run / 14.0) * 40.0)

    return IntelligenceScoreBundle(
        identity_confidence=identity * 100.0 if identity <= 1 else identity,
        evidence_strength=evidence,
        relationship_confidence=relations,
        behavior_stability=behavior,
        source_reliability=source_rel,
        case_completeness=completeness,
        hypothesis_confidence=hyp_conf,
        investigation_progress=progress,
    )
