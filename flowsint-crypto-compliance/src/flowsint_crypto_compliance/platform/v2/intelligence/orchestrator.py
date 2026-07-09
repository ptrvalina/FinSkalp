"""Intelligence Platform orchestrator — RFC-0004."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.ingest_pipeline import get_ingest_pipeline
from flowsint_crypto_compliance.platform.v2.intelligence.engines import (
    AttributionIntelligenceEngine,
    BehavioralIntelligenceEngine,
    BlockchainIntelligenceEngine,
    CorrelationIntelligenceEngine,
    EntityResolutionIntelligenceEngine,
    ExplainIntelligenceEngine,
    OsintIntelligenceEngine,
    RecommendationIntelligenceEngine,
    RegistryIntelligenceEngine,
    RiskIntelligenceEngine,
    TimelineIntelligenceEngine,
)
from flowsint_crypto_compliance.platform.v2.intelligence.manifest import intelligence_platform_manifest
from flowsint_crypto_compliance.platform.v2.intelligence.types import (
    EngineAnalysisResult,
    IntelligenceContext,
    IntelligenceRunResult,
)
from flowsint_crypto_compliance.platform.v2.knowledge_graph import get_knowledge_graph_service


def get_intelligence_engines():
    """Ordered pipeline — Risk and Recommendation run last."""
    return [
        BlockchainIntelligenceEngine(),
        OsintIntelligenceEngine(),
        RegistryIntelligenceEngine(),
        BehavioralIntelligenceEngine(),
        EntityResolutionIntelligenceEngine(),
        CorrelationIntelligenceEngine(),
        AttributionIntelligenceEngine(),
        TimelineIntelligenceEngine(),
        RiskIntelligenceEngine(),
        ExplainIntelligenceEngine(),
        RecommendationIntelligenceEngine(),
    ]


class IntelligenceOrchestrator:
    """
    Runs all RFC-0004 engines over Knowledge Graph context.
    Publishes findings via mandatory IngestPipeline.
    """

    def __init__(self) -> None:
        self._engines = get_intelligence_engines()
        self._kg = get_knowledge_graph_service()
        self._ingest = get_ingest_pipeline()

    def manifest(self) -> dict[str, Any]:
        return intelligence_platform_manifest(self._engines)

    def run(self, ctx: IntelligenceContext, *, publish: bool = True) -> IntelligenceRunResult:
        result = IntelligenceRunResult()
        all_findings: list[dict[str, Any]] = []
        engine_results: list[EngineAnalysisResult] = []

        # Enrich context from KG
        if ctx.entity_id:
            ctx.kg_neighbors = self._kg.get_neighbors(ctx.entity_id)

        screening = dict(ctx.screening or {})

        for engine in self._engines:
            if engine.kind.value in ("correlation", "risk", "explain", "recommendation"):
                screening["_intel_findings"] = all_findings
            if engine.kind.value == "explain":
                screening["_intel_engine_results"] = [r.to_dict() for r in engine_results]
            ctx.screening = screening

            try:
                er = engine.analyze(ctx)
                engine_results.append(er)
                result.engines_run.append(engine.kind.value)
                for f in er.findings:
                    all_findings.append(f.to_dict())
                    if publish and f.entity_value and f.entity_type:
                        self._publish_finding(ctx, f, result)
            except Exception as exc:
                result.errors.append(f"{engine.kind.value}: {exc}")

        # Risk aggregate for recommendations
        risk_result = next((r for r in engine_results if r.engine.value == "risk"), None)
        if risk_result and risk_result.findings:
            agg = risk_result.findings[0].explain.get("aggregate_risk_score", 0)
            screening["_aggregate_risk"] = agg
            result.aggregate_risk_score = float(agg)
            result.risk_level = risk_result.findings[0].explain.get("risk_level", "low")
            ctx.screening = screening

        rec_result = next((r for r in engine_results if r.engine.value == "recommendation"), None)
        if rec_result and rec_result.findings:
            result.recommendations = rec_result.findings[0].explain.get("recommendations") or []

        explain_result = next((r for r in engine_results if r.engine.value == "explain"), None)
        if explain_result and explain_result.findings:
            result.explain = explain_result.findings[0].explain

        result.engine_results = engine_results
        result.ok = bool(result.engine_results) and len(result.errors) < len(self._engines)
        return result

    def _publish_finding(self, ctx: IntelligenceContext, finding, result: IntelligenceRunResult) -> None:
        ing = self._ingest.ingest(
            tenant_id=ctx.tenant_id,
            source_type=f"intelligence.{finding.engine.value}",
            entity_type=finding.entity_type or "blockchain_address",
            entity_value=finding.entity_value or ctx.address or "unknown",
            chain=ctx.chain,
            case_ref=ctx.case_ref,
            actor=f"intelligence.{finding.engine.value}",
            confidence=finding.confidence,
            payload={
                "finding": finding.to_dict(),
                "investigation_id": str(ctx.investigation_id) if ctx.investigation_id else None,
            },
            require_relation_evidence=False,
        )
        if ing.evidence_id:
            result.published_evidence_ids.append(str(ing.evidence_id))


_orchestrator: IntelligenceOrchestrator | None = None


def get_intelligence_orchestrator() -> IntelligenceOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = IntelligenceOrchestrator()
    return _orchestrator


def run_intelligence_analysis(
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
) -> IntelligenceRunResult:
    ctx = IntelligenceContext(
        tenant_id=tenant_id,
        entity_id=entity_id,
        address=address,
        chain=chain,
        case_ref=case_ref,
        investigation_id=investigation_id,
        screening=screening or {},
        attribution=attribution or {},
        mentions=mentions or [],
    )
    return get_intelligence_orchestrator().run(ctx, publish=publish)
