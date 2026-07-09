"""RFC-0014 Ch.1 — ICF pipeline orchestrator."""

from __future__ import annotations

import time
import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors import get_connector_registry
from flowsint_crypto_compliance.platform.v2.icf.collector import ICFCollector
from flowsint_crypto_compliance.platform.v2.icf.evidence import get_evidence_generator
from flowsint_crypto_compliance.platform.v2.icf.entity_extractor import get_entity_extractor
from flowsint_crypto_compliance.platform.v2.icf.fusion_bridge import run_fusion_bridge
from flowsint_crypto_compliance.platform.v2.icf.kg_bridge import ingest_records
from flowsint_crypto_compliance.platform.v2.icf.monitoring import get_icf_monitoring
from flowsint_crypto_compliance.platform.v2.icf.quality import get_quality_engine
from flowsint_crypto_compliance.platform.v2.icf.sources import resolve_source_category
from flowsint_crypto_compliance.platform.v2.icf.types import ICFPipelineResult, ICFStage


async def run_icf_pipeline(
    *,
    connector_id: str,
    tenant_id: uuid.UUID,
    query: dict[str, Any] | None = None,
    case_ref: str | None = None,
    publish: bool = True,
) -> ICFPipelineResult:
    """
    Main ICF entry — wires all stages explicitly.
    Collector MUST NOT mutate graph/risk/ER; fusion + kg bridges handle downstream.
    """
    started = time.perf_counter()
    monitoring = get_icf_monitoring()
    result = ICFPipelineResult(ok=True, connector_id=connector_id, source_category="unknown")
    stages: list[str] = []

    try:
        registry = get_connector_registry()
        descriptor = registry.get_descriptor(connector_id)
        if not descriptor:
            raise ValueError(f"Unknown connector: {connector_id}")

        source_cat = resolve_source_category(descriptor.category)
        result.source_category = source_cat.value
        stages.append(ICFStage.SOURCE.value)
        result.explain["source"] = {"category": source_cat.value, "connector_id": connector_id}

        connector = registry.create(connector_id)
        collector = ICFCollector(connector)
        stages.append(ICFStage.COLLECTOR.value)

        await collector.initialize()
        await collector.authenticate()
        raw = await collector.collect(query=query)
        result.records = raw

        normalized = collector.normalize(raw)
        stages.append(ICFStage.NORMALIZER.value)
        result.normalized = normalized

        valid, val_errors = collector.validate(normalized)
        stages.append(ICFStage.VALIDATOR.value)
        result.errors.extend(val_errors)

        extracted = get_entity_extractor().extract_from_records(
            valid,
            connector_id=connector_id,
            provenance_base={"case_ref": case_ref, "tenant_id": str(tenant_id)},
        )
        stages.append(ICFStage.ENTITY_EXTRACTOR.value)
        result.extracted_entities = extracted

        combined = valid + extracted
        evidence = get_evidence_generator().generate(
            combined,
            tenant_id=tenant_id,
            connector_id=connector_id,
            case_ref=case_ref,
        )
        stages.append(ICFStage.EVIDENCE_GENERATOR.value)
        result.evidence = evidence

        quality = get_quality_engine().score(
            profile=descriptor.quality,
            records=combined,
            validation_errors=val_errors,
        )
        result.quality_score = quality.composite
        result.explain["quality"] = quality.to_dict()

        fusion_events = 0
        kg_ingested = 0
        if publish and combined:
            fusion_result = await run_fusion_bridge(
                combined,
                tenant_id=tenant_id,
                case_ref=case_ref,
            )
            stages.append(ICFStage.FUSION.value)
            fusion_events = fusion_result.get("events_emitted", 0)
            result.explain["fusion"] = fusion_result

            kg_result = ingest_records(
                combined,
                tenant_id=tenant_id,
                case_ref=case_ref,
                actor=f"icf.{connector_id}",
            )
            stages.append(ICFStage.KNOWLEDGE_GRAPH.value)
            kg_ingested = kg_result.get("ingested", 0)
            result.explain["knowledge_graph"] = kg_result
            if kg_result.get("errors"):
                result.errors.extend(kg_result["errors"])

        result.fusion_events = fusion_events
        result.kg_ingested = kg_ingested

        await collector.shutdown()
        result.ok = bool(combined) or not val_errors

        latency_ms = (time.perf_counter() - started) * 1000
        monitoring.record_request(
            connector_id,
            latency_ms=latency_ms,
            success=result.ok,
            records=len(combined),
            connected=True,
        )
    except Exception as exc:
        result.ok = False
        result.errors.append(str(exc))
        monitoring.record_request(connector_id, latency_ms=0, success=False, connected=False)

    result.stages = stages
    return result
