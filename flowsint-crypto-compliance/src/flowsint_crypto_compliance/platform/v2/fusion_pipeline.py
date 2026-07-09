"""Intelligence Fusion pipeline — RFC-0002 L2 + RFC-0003 extended stages."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus


class FusionStage(str, Enum):
    # RFC-0002 core stages
    VALIDATE = "validate"
    NORMALIZE = "normalize"
    DEDUPLICATE = "deduplicate"
    ENRICH = "enrich"
    ATTRIBUTE = "attribute"
    CONFIDENCE = "confidence"
    PUBLISH = "publish"
    # RFC-0003 extensions
    CLEAN = "clean"
    QUALITY_CHECK = "quality_check"
    ENTITY_RESOLUTION = "entity_resolution"
    RELATION_CREATE = "relation_create"
    GRAPH_PUBLISH = "graph_publish"


RFC0002_STAGES: tuple[FusionStage, ...] = (
    FusionStage.VALIDATE,
    FusionStage.NORMALIZE,
    FusionStage.DEDUPLICATE,
    FusionStage.ENRICH,
    FusionStage.ATTRIBUTE,
    FusionStage.CONFIDENCE,
    FusionStage.PUBLISH,
)

RFC0003_EXTRA_STAGES: tuple[FusionStage, ...] = (
    FusionStage.CLEAN,
    FusionStage.QUALITY_CHECK,
    FusionStage.ENTITY_RESOLUTION,
    FusionStage.RELATION_CREATE,
    FusionStage.GRAPH_PUBLISH,
)


StageHandler = Callable[[list[dict[str, Any]], dict[str, Any]], Awaitable[list[dict[str, Any]]]]


@dataclass
class FusionPipeline:
    """Orchestrates fusion stages; emits PlatformEvent per stage completion."""

    source: str = "finskalp.fusion"
    handlers: dict[FusionStage, StageHandler] = field(default_factory=dict)
    include_rfc0003: bool = False

    def __post_init__(self) -> None:
        for stage in FusionStage:
            self.handlers.setdefault(stage, self._default_handler(stage))
        self._wire_rfc0003_defaults()

    def _stages_to_run(self) -> tuple[FusionStage, ...]:
        if self.include_rfc0003:
            return RFC0002_STAGES + RFC0003_EXTRA_STAGES
        return RFC0002_STAGES

    async def run(
        self,
        raw_records: list[dict[str, Any]],
        *,
        tenant_id: uuid.UUID | None = None,
        investigation_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
        context: dict[str, Any] | None = None,
        include_rfc0003: bool | None = None,
    ) -> list[PlatformEvent]:
        ctx = dict(context or {})
        ctx["tenant_id"] = tenant_id
        ctx["investigation_id"] = investigation_id
        bus = get_platform_event_bus()
        emitted: list[PlatformEvent] = []
        records = list(raw_records)

        use_rfc3 = self.include_rfc0003 if include_rfc0003 is None else include_rfc0003
        stages = RFC0002_STAGES + RFC0003_EXTRA_STAGES if use_rfc3 else RFC0002_STAGES

        stage_event_map = {
            FusionStage.VALIDATE: EventType.RAW_DATA_VALIDATED,
            FusionStage.NORMALIZE: EventType.DATA_NORMALIZED,
            FusionStage.DEDUPLICATE: EventType.DUPLICATE_SUPPRESSED,
            FusionStage.ENRICH: EventType.ENTITY_ENRICHED,
            FusionStage.ATTRIBUTE: EventType.ATTRIBUTION_APPLIED,
            FusionStage.CONFIDENCE: EventType.CONFIDENCE_CALCULATED,
            FusionStage.PUBLISH: EventType.FUSED_INTELLIGENCE_READY,
            FusionStage.CLEAN: EventType.DATA_NORMALIZED,
            FusionStage.QUALITY_CHECK: EventType.RAW_DATA_VALIDATED,
            FusionStage.ENTITY_RESOLUTION: EventType.ENTITY_MERGED,
            FusionStage.RELATION_CREATE: EventType.EVIDENCE_CREATED,
            FusionStage.GRAPH_PUBLISH: EventType.FUSED_INTELLIGENCE_READY,
        }

        for stage in stages:
            records = await self.handlers[stage](records, ctx)
            ev = PlatformEvent(
                event_type=stage_event_map[stage],
                source=self.source,
                tenant_id=tenant_id,
                investigation_id=investigation_id,
                correlation_id=correlation_id,
                payload={"stage": stage.value, "record_count": len(records), **ctx.get("stage_payload", {})},
            )
            bus.publish(ev)
            emitted.append(ev)

        return emitted

    @staticmethod
    def _default_handler(stage: FusionStage) -> StageHandler:
        async def _pass(records: list[dict[str, Any]], _ctx: dict[str, Any]) -> list[dict[str, Any]]:
            return records

        return _pass

    def _wire_rfc0003_defaults(self) -> None:
        from flowsint_crypto_compliance.platform.v2.ingest_pipeline import get_ingest_pipeline

        pipeline = get_ingest_pipeline()

        async def _clean(records: list[dict[str, Any]], _ctx: dict[str, Any]) -> list[dict[str, Any]]:
            cleaned = []
            for r in records:
                if not r:
                    continue
                cleaned.append({k: v for k, v in r.items() if v is not None and v != ""})
            return cleaned

        async def _quality(records: list[dict[str, Any]], ctx: dict[str, Any]) -> list[dict[str, Any]]:
            passed = [r for r in records if r.get("entity_value") or r.get("address") or r.get("confidence")]
            ctx["stage_payload"] = {"quality_passed": len(passed), "quality_rejected": len(records) - len(passed)}
            return passed

        async def _entity_resolution(records: list[dict[str, Any]], ctx: dict[str, Any]) -> list[dict[str, Any]]:
            tenant = ctx.get("tenant_id")
            if not tenant:
                return records
            out = []
            for r in records:
                et = r.get("entity_type") or ("crypto_address" if r.get("address") else "unknown")
                val = r.get("entity_value") or r.get("address") or ""
                if not val:
                    out.append(r)
                    continue
                result = pipeline.ingest(
                    tenant_id=uuid.UUID(str(tenant)),
                    source_type=str(r.get("source_type", "fusion")),
                    entity_type=str(et),
                    entity_value=str(val),
                    payload=r,
                    chain=r.get("chain"),
                    confidence=float(r.get("confidence") or 0.5),
                    require_relation_evidence=False,
                )
                r["entity_id"] = str(result.entity_id) if result.entity_id else None
                r["evidence_id"] = str(result.evidence_id) if result.evidence_id else None
                r["merge_decision"] = result.merge_decision
                out.append(r)
            return out

        async def _relation_create(records: list[dict[str, Any]], ctx: dict[str, Any]) -> list[dict[str, Any]]:
            return records

        async def _graph_publish(records: list[dict[str, Any]], ctx: dict[str, Any]) -> list[dict[str, Any]]:
            ctx["stage_payload"] = {"graph_published": len(records)}
            return records

        self.handlers[FusionStage.CLEAN] = _clean
        self.handlers[FusionStage.QUALITY_CHECK] = _quality
        self.handlers[FusionStage.ENTITY_RESOLUTION] = _entity_resolution
        self.handlers[FusionStage.RELATION_CREATE] = _relation_create
        self.handlers[FusionStage.GRAPH_PUBLISH] = _graph_publish

    def with_handler(self, stage: FusionStage, handler: StageHandler) -> FusionPipeline:
        self.handlers[stage] = handler
        return self

    @staticmethod
    def with_bayesian_confidence(*, include_rfc0003: bool = False) -> FusionPipeline:
        """Wire existing osint fusion_confidence into CONFIDENCE stage."""
        from flowsint_crypto_compliance.osint.fusion_confidence import EvidenceFinding, fuse_evidence

        async def _confidence(records: list[dict[str, Any]], ctx: dict[str, Any]) -> list[dict[str, Any]]:
            findings = [
                EvidenceFinding(
                    source_type=r.get("source_type", "unknown"),
                    raw_confidence=float(r.get("confidence", 0.5)),
                    source_name=r.get("source_name"),
                    dependency_group=r.get("dependency_group"),
                )
                for r in records
            ]
            if findings:
                result = fuse_evidence(findings)
                ctx["stage_payload"] = {
                    "composite_pct": round(result.composite_confidence * 100, 1),
                    "explain_count": len(result.explain),
                }
                for r in records:
                    r["fusion_confidence"] = result.composite_confidence
            return records

        pipe = FusionPipeline(include_rfc0003=include_rfc0003)
        pipe.handlers[FusionStage.CONFIDENCE] = _confidence
        return pipe

    @staticmethod
    def with_rfc0003_path() -> FusionPipeline:
        """Full RFC-0003 fusion path including ingest pipeline stages."""
        return FusionPipeline.with_bayesian_confidence(include_rfc0003=True)


def default_fusion_pipeline() -> FusionPipeline:
    """Resolve fusion mode from FINSKALP_FUSION_MODE (default rfc0003)."""
    import os

    mode = os.getenv("FINSKALP_FUSION_MODE", "rfc0003").strip().lower()
    if mode == "rfc0003":
        return FusionPipeline.with_rfc0003_path()
    return FusionPipeline.with_bayesian_confidence()
