"""In-memory compliance orchestration for demo stand (no database)."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.demo.demo_context import (
    get_demo_chain_adapters,
    get_demo_label_cache,
    seed_demo_registry,
)
from flowsint_crypto_compliance.demo.scenarios import get_scenario
from flowsint_crypto_compliance.ingestion.bank_regulator import bank_feed_to_fiat_event
from flowsint_crypto_compliance.ingestion.hub_rows import bank_feed_to_hub_row
from flowsint_crypto_compliance.ingestion.registry_staging import stage_registry_lines
from flowsint_crypto_compliance.osint_core.fusion_engine import InvestigationBundle, OSINTFusionEngine
from flowsint_crypto_compliance.reporting.regulator_report import ReportBuilder
from flowsint_crypto_compliance.schemas.hub import hub_row_to_bank_feed, validate_bank_feed_batch
from flowsint_crypto_compliance.services.compliance_service import _serialize_evidence_graph
from flowsint_crypto_compliance.platform.v2.neo4j_projection import project_evidence_graph
from flowsint_crypto_compliance.storage.neo4j_exporter import EvidenceGraphNeo4jExporter
from flowsint_crypto_compliance.storage.neo4j_pivots import ComplianceNeo4jPivotExporter
from flowsint_types.fiat_crypto import ControlPurchaseEvent, LicensedPlatformEvent

_store: "DemoComplianceStore | None" = None


@dataclass
class DemoCase:
    id: uuid.UUID
    case_ref: str
    status: str = "draft"
    fusion_result: dict[str, Any] | None = None
    bank_feeds: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DemoComplianceStore:
    def __init__(self) -> None:
        self.cases: dict[uuid.UUID, DemoCase] = {}
        self.cases_by_ref: dict[str, uuid.UUID] = {}

    def create_case(self, *, case_ref: str) -> DemoCase:
        case = DemoCase(id=uuid.uuid4(), case_ref=case_ref)
        self.cases[case.id] = case
        self.cases_by_ref[case.case_ref] = case.id
        return case

    def get_case(self, case_id: uuid.UUID) -> DemoCase | None:
        return self.cases.get(case_id)

    def get_case_by_ref(self, case_ref: str) -> DemoCase | None:
        cid = self.cases_by_ref.get(case_ref)
        return self.cases.get(cid) if cid else None


class DemoComplianceService:
    """Mirrors ComplianceService API using RAM + seeded sovereign registry."""

    def __init__(self, store: DemoComplianceStore | None = None) -> None:
        self._store = store or DemoComplianceStore()
        self._cache = get_demo_label_cache()

    @property
    def store(self) -> DemoComplianceStore:
        return self._store

    def create_case(self, *, case_ref: str, owner_id: uuid.UUID | None = None) -> DemoCase:
        if self._store.get_case_by_ref(case_ref):
            raise ValueError("case_ref already exists")
        return self._store.create_case(case_ref=case_ref)

    def get_case(self, case_id: uuid.UUID) -> DemoCase | None:
        return self._store.get_case(case_id)

    def get_case_by_ref(self, case_ref: str) -> DemoCase | None:
        return self._store.get_case_by_ref(case_ref)

    def ingest_bank_feed_batch(self, case_id: uuid.UUID, payload: dict[str, Any]) -> int:
        validate_bank_feed_batch(payload)
        case = self.get_case(case_id)
        if not case:
            raise ValueError("Case not found")
        case.bank_feeds = list(payload["feeds"])
        case.status = "ingesting"
        return len(case.bank_feeds)

    def import_registry_jsonl_lines(self, lines: list[str]) -> int:
        labels = stage_registry_lines(lines)
        return self._cache.bulk_upsert(labels)

    def import_registry_parquet(self, path) -> int:
        from pathlib import Path

        from flowsint_crypto_compliance.ingestion.registry_staging import stage_registry_parquet

        labels = stage_registry_parquet(Path(path))
        return self._cache.bulk_upsert(labels)

    async def fuse_case(
        self,
        case_id: uuid.UUID,
        *,
        licensed_events: list[LicensedPlatformEvent] | None = None,
        control_purchases: list[ControlPurchaseEvent] | None = None,
        chain_adapters: dict | None = None,
        scenario_id: str | None = None,
    ) -> dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError("Case not found")

        bank_feeds = [hub_row_to_bank_feed(row) for row in case.bank_feeds]
        fiat_events = [bank_feed_to_fiat_event(b) for b in bank_feeds]

        engine = OSINTFusionEngine(
            chain_adapters=chain_adapters or get_demo_chain_adapters(scenario_id),
            label_cache=self._cache,
        )
        bundle = InvestigationBundle(
            case_id=case.case_ref,
            bank_feeds=bank_feeds,
            fiat_events=fiat_events,
            licensed_events=licensed_events or [],
            control_purchases=control_purchases or [],
        )
        result = await engine.fuse(bundle)

        evidence_graph = _serialize_evidence_graph(result.graph)
        neo4j_unified = project_evidence_graph(result.graph, case_ref=case.case_ref)
        neo4j_export = EvidenceGraphNeo4jExporter().export(
            result.graph,
            case_ref=case.case_ref,
        )
        neo4j_pivots = ComplianceNeo4jPivotExporter().export(
            result.graph,
            case_ref=case.case_ref,
        )

        fusion_payload = {
            "case_ref": case.case_ref,
            "attributions": [a.model_dump() for a in result.attributions],
            "bridges": [b.model_dump() for b in result.bridges],
            "linkage_scores": result.linkage_scores,
            "graph_stats": {
                "nodes": len(result.graph.nodes),
                "edges": len(result.graph.edges),
            },
            "evidence_graph": evidence_graph,
            "neo4j_unified": neo4j_unified,
            "neo4j_export": neo4j_export,
            "neo4j_pivots": neo4j_pivots,
        }
        case.fusion_result = fusion_payload
        case.status = "fused"
        return fusion_payload

    async def fuse_case_with_report(
        self,
        case_id: uuid.UUID,
        *,
        scenario_title_ru: str = "Расследование",
        licensed_events: list[LicensedPlatformEvent] | None = None,
        control_purchases: list[ControlPurchaseEvent] | None = None,
        chain_adapters: dict | None = None,
        scenario_id: str | None = None,
    ) -> dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            raise ValueError("Case not found")

        bank_feeds = [hub_row_to_bank_feed(row) for row in case.bank_feeds]
        fiat_events = [bank_feed_to_fiat_event(b) for b in bank_feeds]

        engine = OSINTFusionEngine(
            chain_adapters=chain_adapters or get_demo_chain_adapters(scenario_id),
            label_cache=self._cache,
        )
        bundle = InvestigationBundle(
            case_id=case.case_ref,
            bank_feeds=bank_feeds,
            fiat_events=fiat_events,
            licensed_events=licensed_events or [],
            control_purchases=control_purchases or [],
        )
        result = await engine.fuse(bundle)
        report = ReportBuilder().build(
            case_ref=case.case_ref,
            scenario_title_ru=scenario_title_ru,
            fusion=result,
            bank_feed_count=len(bank_feeds),
            control_purchase_count=len(control_purchases or []),
            registry_label_count=self._cache.count(),
        )
        payload = report.to_dict()
        payload["graph_stats"] = {
            "nodes": len(result.graph.nodes),
            "edges": len(result.graph.edges),
        }
        payload["evidence_graph"] = _serialize_evidence_graph(result.graph)
        payload["neo4j_unified"] = project_evidence_graph(result.graph, case_ref=case.case_ref)
        payload["neo4j_export"] = EvidenceGraphNeo4jExporter().export(
            result.graph,
            case_ref=case.case_ref,
        )
        payload["neo4j_pivots"] = ComplianceNeo4jPivotExporter().export(
            result.graph,
            case_ref=case.case_ref,
        )
        case.fusion_result = payload
        case.status = "reported"
        return payload

    async def seed_scenario(self, scenario_id: str) -> dict[str, Any]:
        scenario = get_scenario(scenario_id)
        for label in scenario.registry_labels:
            self._cache.put(label)

        existing = self.get_case_by_ref(scenario.case_ref)
        case = existing or self._store.create_case(case_ref=scenario.case_ref)

        bank_batch = {
            "schema_version": "regulator-hub/v1",
            "hub_id": "demo-fiu-hub-ru",
            "feeds": [bank_feed_to_hub_row(b) for b in scenario.bank_feeds],
        }
        self.ingest_bank_feed_batch(case.id, bank_batch)
        return await self.fuse_case_with_report(
            case.id,
            scenario_title_ru=scenario.title_ru,
            licensed_events=scenario.licensed_events,
            control_purchases=scenario.control_purchases,
            chain_adapters=get_demo_chain_adapters(scenario_id),
            scenario_id=scenario_id,
        )

    def fuse_case_sync(self, *args, **kwargs) -> dict[str, Any]:
        return asyncio.run(self.fuse_case(*args, **kwargs))


def get_demo_compliance_service() -> DemoComplianceService:
    global _store
    if _store is None:
        _store = DemoComplianceStore()
        seed_demo_registry()
    return DemoComplianceService(_store)
