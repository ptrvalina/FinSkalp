"""RFC-0006 Intelligence Engine orchestrator."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.intelligence import run_intelligence_analysis
from flowsint_crypto_compliance.platform.v2.intelligence_engine.behavior import analyze_behavior_habits
from flowsint_crypto_compliance.platform.v2.intelligence_engine.fusion import run_fusion_intelligence
from flowsint_crypto_compliance.platform.v2.intelligence_engine.hypotheses import generate_hypotheses
from flowsint_crypto_compliance.platform.v2.intelligence_engine.memory import learn_from_case, memory_manifest
from flowsint_crypto_compliance.platform.v2.intelligence_engine.patterns import detect_patterns
from flowsint_crypto_compliance.platform.v2.intelligence_engine.pipeline import (
    RFC0006_PIPELINE,
    intelligence_pipeline_manifest,
)
from flowsint_crypto_compliance.platform.v2.intelligence_engine.scores import calculate_intelligence_scores
from flowsint_crypto_compliance.platform.v2.intelligence_engine.types import (
    IntelligenceEngineContext,
    IntelligenceEngineResult,
    IntelligenceQuestion,
)


class IntelligenceEngineOrchestrator:
    """RFC-0006 full pipeline over KG context + RFC-0004 engines."""

    def manifest(self) -> dict[str, Any]:
        base = intelligence_pipeline_manifest()
        base["memory"] = memory_manifest()
        base["api"] = {
            "manifest": "/api/platform/v2/intelligence-engine/manifest",
            "run": "POST /api/platform/v2/intelligence-engine/run",
        }
        return base

    def run(
        self,
        ctx: IntelligenceEngineContext,
        *,
        publish: bool = True,
        learn_memory: bool = True,
    ) -> IntelligenceEngineResult:
        result = IntelligenceEngineResult()
        stages: list[str] = []

        # Collector / normalizer / validator via fusion intelligence
        records = list(ctx.mentions) + list(ctx.fusion_records)
        fusion_out = run_fusion_intelligence(records, context={"case_ref": ctx.case_ref})
        stages.extend(["source", "collector", "normalizer", "validator"])
        result.explain["fusion_intelligence"] = fusion_out

        trust_vals = [
            float(r.get("_fusion", {}).get("trust", 0.5))
            for r in fusion_out.get("records") or []
            if isinstance(r, dict)
        ]
        fusion_trust_avg = sum(trust_vals) / len(trust_vals) if trust_vals else 0.5

        stages.extend(["entity_resolution", "knowledge_graph", "correlation"])

        # RFC-0004 analytics layer
        intel = run_intelligence_analysis(
            tenant_id=ctx.tenant_id,
            address=ctx.address,
            chain=ctx.chain,
            case_ref=ctx.case_ref,
            investigation_id=ctx.investigation_id,
            entity_id=ctx.entity_id,
            screening=ctx.screening,
            attribution=ctx.attribution,
            mentions=ctx.mentions,
            publish=publish,
        )
        prior = []
        for er in intel.engine_results:
            for f in er.findings:
                prior.append(f.to_dict())
        ctx.prior_findings = prior
        stages.extend(["pattern_detection", "behavior_analysis", "risk"])

        result.patterns = detect_patterns(ctx)
        behavior_hits, behavior_meta = analyze_behavior_habits(ctx)
        result.patterns.extend(behavior_hits)

        result.hypotheses = generate_hypotheses(ctx, result.patterns, prior)
        stages.append("hypothesis_generator")

        result.recommendations = list(intel.recommendations or [])
        for h in result.hypotheses:
            if h.confidence >= 0.6:
                result.recommendations.append({
                    "action_ru": f"Проверить гипотезу: {h.statement_ru[:80]}…",
                    "priority": "medium",
                    "hypothesis_code": h.code,
                })

        result.explain["ai_explanation"] = {
            "engines_run": intel.engines_run,
            "explain": intel.explain,
            "rules_ru": "Без объяснения интеллект запрещается использовать",
        }
        stages.append("ai_explanation")

        evidence_count = len(intel.published_evidence_ids) + len(ctx.mentions)
        result.scores = calculate_intelligence_scores(
            ctx,
            patterns=result.patterns,
            hypotheses=result.hypotheses,
            evidence_count=evidence_count,
            engines_run=len(intel.engines_run),
            behavior_stability=float(behavior_meta.get("behavior_stability") or 0.7),
            fusion_trust_avg=fusion_trust_avg,
        )
        result.explain["behavior"] = behavior_meta
        result.explain["patterns_count"] = len(result.patterns)

        result.questions_answered = _answer_questions(ctx, result, intel)
        stages.extend(["investigation", "report"])
        result.pipeline_stages = stages

        if learn_memory and ctx.case_ref:
            result.memory_updates = learn_from_case(
                case_ref=ctx.case_ref,
                patterns=[p.to_dict() for p in result.patterns],
                hypotheses=[h.to_dict() for h in result.hypotheses],
                scores=result.scores.to_dict(),
            )

        result.ok = intel.ok and len(stages) >= len(RFC0006_PIPELINE) - 2
        result.published_evidence_ids = list(intel.published_evidence_ids)
        if intel.errors:
            result.errors.extend(intel.errors)
        return result


def _answer_questions(ctx: IntelligenceEngineContext, result: IntelligenceEngineResult, intel: Any) -> dict[str, str]:
    onchain = (ctx.screening or {}).get("onchain_summary") or {}
    return {
        IntelligenceQuestion.WHAT_HAPPENED.value: (
            f"Активность: in={onchain.get('inbound_count', 0)}, out={onchain.get('outbound_count', 0)}; "
            f"паттернов: {len(result.patterns)}"
        ),
        IntelligenceQuestion.WHY_HAPPENED.value: str(
            (intel.explain or {}).get("rules_fired") or result.explain.get("fusion_intelligence", {}).get("explain_ru")
        )[:200],
        IntelligenceQuestion.WHO_INVOLVED.value: f"Упоминаний: {len(ctx.mentions)}; меток: {len((ctx.attribution or {}).get('labels') or {})}",
        IntelligenceQuestion.WHAT_LINKED.value: f"Гипотез: {len(result.hypotheses)}; корреляций в prior: {len(ctx.prior_findings)}",
        IntelligenceQuestion.WHAT_TO_CHECK.value: f"Рекомендаций: {len(result.recommendations)}; слабый показатель: {result.scores.weakest()[0]}",
    }


_orchestrator: IntelligenceEngineOrchestrator | None = None


def get_intelligence_engine_orchestrator() -> IntelligenceEngineOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = IntelligenceEngineOrchestrator()
    return _orchestrator


def run_intelligence_engine(
    *,
    tenant_id: uuid.UUID,
    case_ref: str | None = None,
    investigation_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    address: str | None = None,
    chain: str | None = None,
    screening: dict[str, Any] | None = None,
    attribution: dict[str, Any] | None = None,
    mentions: list[dict[str, Any]] | None = None,
    publish: bool = True,
    learn_memory: bool = True,
) -> IntelligenceEngineResult:
    ctx = IntelligenceEngineContext(
        tenant_id=tenant_id,
        case_ref=case_ref,
        investigation_id=investigation_id,
        entity_id=entity_id,
        address=address,
        chain=chain,
        screening=screening or {},
        attribution=attribution or {},
        mentions=mentions or [],
    )
    return get_intelligence_engine_orchestrator().run(ctx, publish=publish, learn_memory=learn_memory)
