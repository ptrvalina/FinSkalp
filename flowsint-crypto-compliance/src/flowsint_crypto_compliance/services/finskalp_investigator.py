"""FinSkalp — суверенное расследование криптоадресов и транзакций (без иностранного KYT)."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from flowsint_crypto_compliance.chains import get_chain_adapter
from flowsint_crypto_compliance.chains.base import InMemoryChainAdapter, OnChainTransfer
from flowsint_crypto_compliance.demo.combat_mode import is_combat_mode
from flowsint_crypto_compliance.demo.chain_data import DEMO_TRANSFERS, get_demo_adapters
from flowsint_crypto_compliance.attribution import AttributionEngine
from flowsint_crypto_compliance.demo.demo_context import get_demo_label_cache, preload_kyt_samples
from flowsint_crypto_compliance.demo.scenarios import SCENARIOS, get_scenario
from flowsint_crypto_compliance.ingestion.bank_regulator import bank_feed_to_fiat_event
from flowsint_crypto_compliance.osint_core.fusion_engine import InvestigationBundle, OSINTFusionEngine
from flowsint_crypto_compliance.osint_core.scalpel import ScalpelEngine
from flowsint_crypto_compliance.osint_core.multihop_fusion import is_live_address
from flowsint_crypto_compliance.osint_core.open_source_collector import open_osint_findings
from flowsint_crypto_compliance.observability.tracing import span
from flowsint_crypto_compliance.reporting.finskalp_report import FinSkalpReportBuilder
from flowsint_crypto_compliance.reporting.sar_report import SarReportBuilder
from flowsint_crypto_compliance.reporting.seizure_report import SeizureReportBuilder
from flowsint_crypto_compliance.reporting.volumetric_report import VolumetricReportBuilder
from flowsint_crypto_compliance.reporting.regulator_report import ReportBuilder
from flowsint_crypto_compliance.services.wallet_screening import (
    WalletScreeningRequest,
    WalletScreeningService,
    infer_chain,
)
from flowsint_types.fiat_crypto import BankRegulatorFeed, Chain, LicensedPlatformEvent

_PHASES_RU: list[tuple[str, str]] = [
    ("validate", "Валидация адреса и сети"),
    ("screen", "Скрининг кошелька · реестр 115-ФЗ"),
    ("onchain", "On-chain TRON/BTC/ETH"),
    ("open_osint", "FinSkalp Scalpel · clearnet / Tor / paste / username"),
    ("fusion", "OSINT Fusion · граф доказательств"),
    ("attribute", "Суверенная атрибуция РФ/СНГ"),
    ("detect", "Детектор + XGBoost"),
    ("report", "Формирование отчёта ФинСкальп"),
]


@dataclass
class FinSkalpInvestigationRequest:
    address: str
    chain: Chain | None = None
    tx_hash: str | None = None
    bank_reference: str | None = None
    bank_name: str | None = None
    subject_id: str | None = None
    amount: float | None = None
    currency: str | None = None
    region: str = "RU"
    notes: str | None = None
    scenario_id: str | None = None
    depth: int = 1
    osint_depth: int = 2
    limit: int = 300
    collectors: list[str] | None = None
    usernames: list[str] | None = None
    counterparties: list[str] | None = None


@dataclass
class FinSkalpInvestigationResult:
    investigation_id: str
    case_ref: str
    address: str
    chain: Chain
    duration_ms: int
    phases: list[dict[str, Any]]
    screening: dict[str, Any]
    fusion_report: dict[str, Any]
    address_report: dict[str, Any]
    forensic_report: dict[str, Any]
    volumetric_report: dict[str, Any] = field(default_factory=dict)
    sar_report: dict[str, Any] = field(default_factory=dict)
    seizure_report: dict[str, Any] = field(default_factory=dict)
    open_osint: dict[str, Any] = field(default_factory=dict)
    live_fusion: dict[str, Any] = field(default_factory=dict)
    scenario_id: str | None = None
    attachments: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        ra = self.forensic_report.get("risk_assessment")
        if isinstance(ra, dict):
            composite = ra.get("composite_label_ru")
        elif isinstance(ra, list) and ra:
            composite = ra[0].get("weight")
        else:
            composite = None
        return {
            "investigation_id": self.investigation_id,
            "case_ref": self.case_ref,
            "product": "FinSkalp",
            "product_tagline_ru": "Точный срез финансовых потоков",
            "address": self.address,
            "chain": self.chain.value,
            "duration_ms": self.duration_ms,
            "scenario_id": self.scenario_id,
            "phases": self.phases,
            "screening": self.screening,
            "fusion_report": self.fusion_report,
            "address_report": self.address_report,
            "forensic_report": self.forensic_report,
            "open_osint": self.open_osint,
            "live_fusion": self.live_fusion,
            "volumetric_report": self.volumetric_report,
            "sar_report": self.sar_report,
            "seizure_report": self.seizure_report,
            "attachments": self.attachments,
            "summary_ru": self.forensic_report.get("executive_summary", {}).get("text_ru", ""),
            "risk_score": self.screening.get("risk_score"),
            "risk_level": self.screening.get("risk_level"),
            "composite_risk": composite,
        }


class FinSkalpInvestigator:
    """Полный цикл: скрининг → on-chain → fusion → отчёты (address + forensic)."""

    def __init__(self) -> None:
        self._label_cache = get_demo_label_cache()
        preload_kyt_samples(self._label_cache)
        self._attribution = AttributionEngine(label_cache=self._label_cache)
        self._scalpel = ScalpelEngine(timeout=8.0)
        self._reporter = FinSkalpReportBuilder()
        self._regulator = ReportBuilder()
        self._volumetric = VolumetricReportBuilder()
        self._sar = SarReportBuilder()
        self._seizure = SeizureReportBuilder()
        self._last_fusion: Any | None = None

    async def investigate(
        self,
        req: FinSkalpInvestigationRequest,
        *,
        on_phase: Callable[[list[dict[str, Any]]], Awaitable[None] | None] | None = None,
        correlation_id: str | None = None,
    ) -> FinSkalpInvestigationResult:
        with span(
            "finskalp.investigate",
            address=req.address,
            chain=str(req.chain or ""),
            correlation_id=correlation_id,
        ):
            return await self._investigate_impl(req, on_phase=on_phase, correlation_id=correlation_id)

    async def _investigate_impl(
        self,
        req: FinSkalpInvestigationRequest,
        *,
        on_phase: Callable[[list[dict[str, Any]]], Awaitable[None] | None] | None = None,
        correlation_id: str | None = None,
    ) -> FinSkalpInvestigationResult:
        t0 = time.perf_counter()
        phases: list[dict[str, Any]] = []
        address = req.address.strip()
        chain = req.chain or infer_chain(address)
        investigation_id = str(uuid.uuid4())
        from flowsint_crypto_compliance.reporting.forensic_builder import generate_case_ref

        case_ref = generate_case_ref(investigation_id)

        await self._attribution.ensure_bootstrap()

        async def _phase(step_id: str, label_ru: str, detail: str, status: str = "done") -> None:
            phases.append({"id": step_id, "label_ru": label_ru, "status": status, "detail_ru": detail})
            if on_phase:
                maybe = on_phase(list(phases))
                if asyncio.iscoroutine(maybe):
                    await maybe

        await _phase("validate", _PHASES_RU[0][1], f"Сеть: {chain.value.upper()}, адрес принят")

        adapters = self._build_adapters(chain, address, req.scenario_id)
        with span("finskalp.onchain_prefetch", chain=chain.value):
            await _prefetch_adapters_to_memory(adapters, chain, address, limit=req.limit)
        screening_svc = WalletScreeningService(
            chain_adapters=adapters,
            label_cache=self._label_cache,
        )
        with span("finskalp.screening", chain=chain.value, address=address):
            screening = (
                await screening_svc.screen(
                    WalletScreeningRequest(
                        address=address,
                        chain=chain,
                        depth=req.depth,
                        limit=req.limit,
                    )
                )
            ).model_dump(mode="json")
        onchain = screening.get("onchain_summary") or {}
        await _phase(
            "screen",
            _PHASES_RU[1][1],
            f"Риск {screening['risk_score']:.1f}/100 ({screening['risk_level']}), "
            f"меток: {len(screening.get('findings') or [])}",
        )
        await _phase(
            "onchain",
            _PHASES_RU[2][1],
            f"Входящих: {onchain.get('inbound_count', 0)}, "
            f"исходящих: {onchain.get('outbound_count', 0)}, "
            f"контрагентов: {onchain.get('counterparties', 0)}",
        )

        counterparties = list(
            dict.fromkeys([*(req.counterparties or []), *_extract_counterparties(screening)])
        )
        with span("finskalp.scalpel", depth=req.osint_depth, collectors=len(req.collectors or [])):
            scalpel_result = await self._scalpel.collect(
                address,
                chain,
                counterparties=counterparties or None,
                depth=req.osint_depth,
                collectors=req.collectors,
                usernames=req.usernames,
            )
        open_result = scalpel_result.to_open_osint_result()
        open_dict = scalpel_result.to_dict()
        fusion_block = scalpel_result.fusion_confidence or open_dict.get("fusion_confidence") or {}
        osint_findings = open_osint_findings(open_result, fusion=fusion_block)
        institutional: dict[str, Any] = {}
        try:
            from flowsint_crypto_compliance.osint.institutional_memory import (
                cross_reference_closed_cases,
                extract_entities_from_osint,
                index_findings_from_scalpel,
            )
            import os as _os

            tenant = _os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
            index_findings_from_scalpel(
                tenant_id=tenant,
                case_id=investigation_id,
                case_ref=case_ref,
                extracted_entities=scalpel_result.extracted_entities,
                mentions=[m.to_dict() for m in scalpel_result.mentions],
            )
            entities = extract_entities_from_osint(
                scalpel_result.extracted_entities,
                [m.to_dict() for m in scalpel_result.mentions],
            )
            mem = cross_reference_closed_cases(
                tenant_id=tenant,
                entities=entities,
                exclude_case_ref=case_ref,
            )
            institutional = mem.to_dict()
            for match in mem.matches:
                osint_findings.append(
                    {
                        "code": "prior_case_match",
                        "severity": "high",
                        "title_ru": match.title_ru,
                        "description_ru": match.link_ru,
                        "evidence": f"prior_case:{match.prior_case_ref}",
                        "confidence": match.match_strength,
                        "priority_flag": "PRIOR_CASE_MATCH",
                        "prior_case_ref": match.prior_case_ref,
                        "source_type": "prior_case_match",
                    }
                )
        except Exception:
            institutional = {"status": "unavailable"}

        preserved_evidence: list[dict[str, Any]] = []
        try:
            from flowsint_crypto_compliance.osint.evidence_preservation import preserve_mentions

            port = int(__import__("os").getenv("COMPLIANCE_DEMO_PORT", "8877"))
            preserved_evidence = await preserve_mentions(
                [m.to_dict() for m in scalpel_result.mentions],
                case_ref=case_ref,
                base_api_url=f"http://localhost:{port}",
                max_urls=4,
            )
        except Exception:
            pass
        open_dict["institutional_memory"] = institutional
        open_dict["preserved_evidence"] = preserved_evidence
        open_dict["fusion_confidence"] = fusion_block

        for label in open_result.proposed_labels:
            self._label_cache.put(label)
        screening["findings"] = list(screening.get("findings") or []) + osint_findings
        if open_result.open_risk_score > 0:
            blended = min(
                100.0,
                float(screening["risk_score"]) * 0.7 + open_result.open_risk_score * 0.3,
            )
            screening["risk_score"] = round(blended, 1)
            screening["open_osint_boost"] = round(open_result.open_risk_score, 1)
        screening["evidence_chain"] = sorted(
            set(screening.get("evidence_chain") or [])
            | {f["evidence"] for f in osint_findings if f.get("evidence")}
        )
        await _phase(
            "open_osint",
            _PHASES_RU[3][1],
            f"Scalpel (depth {req.osint_depth}): {len(scalpel_result.mentions)} сигналов, "
            f"коллекторов: {len(scalpel_result.collectors_run)}, "
            f"веток: {len(scalpel_result.branch_targets)}, "
            f"отсев мусора: {scalpel_result.noise_filter.get('rejected_count', 0)}, "
            f"качество: {scalpel_result.noise_filter.get('quality_score', 0):.0%}, "
            f"open-risk: {open_result.open_risk_score:.0f}/100",
        )

        live_fusion: dict[str, Any] = {}
        if _use_live_chain_adapter(address, chain, req.scenario_id):
            from flowsint_crypto_compliance.ml.scoring_pipeline import score_fusion_graph
            from flowsint_crypto_compliance.osint_core.multihop_fusion import MultiHopFusionEngine
            from flowsint_crypto_compliance.reporting.graph_report import graph_section_for_report
            from flowsint_crypto_compliance.storage.wallet_neo4j import WalletNeo4jStore

            try:
                mh = MultiHopFusionEngine(max_hops=min(req.depth + 2, 3))
                with span("finskalp.live_fusion", chain=chain.value, max_hops=mh._max_hops):
                    fusion_graph = await asyncio.wait_for(
                        mh.explore(address, chain.value),
                        timeout=25.0,
                    )
                live_fusion = fusion_graph.to_dict()
                live_fusion["ml_score"] = score_fusion_graph(
                    live_fusion, address=address, chain=chain.value
                )
                live_fusion["neo4j"] = WalletNeo4jStore().persist_fusion_graph(
                    live_fusion, case_ref=case_ref
                )
                live_fusion["graph_report"] = {
                    k: v for k, v in graph_section_for_report(live_fusion).items() if k != "png_bytes"
                }
                if live_fusion["ml_score"].get("score"):
                    screening["risk_score"] = round(
                        min(
                            100.0,
                            float(screening["risk_score"]) * 0.6
                            + float(live_fusion["ml_score"]["score"]) * 0.4,
                        ),
                        1,
                    )
                await _phase(
                    "live_fusion",
                    "Multi-hop Fusion · live on-chain",
                    f"Граф: {live_fusion.get('node_count', 0)} узлов, "
                    f"{live_fusion.get('edge_count', 0)} рёбер, "
                    f"ML {live_fusion.get('ml_score', {}).get('score', 0)}/100, "
                    f"corridor={'ДА' if live_fusion.get('corridor_flagged') else 'нет'}",
                )
            except asyncio.TimeoutError:
                await _phase("live_fusion", "Multi-hop Fusion", "Таймаут live fusion (25с)", status="warn")
            except Exception as exc:
                await _phase(
                    "live_fusion",
                    "Multi-hop Fusion",
                    f"Ошибка: {exc.__class__.__name__}",
                    status="warn",
                )

        scenario_id = req.scenario_id
        if not is_combat_mode():
            scenario_id = req.scenario_id or match_scenario_for_address(address, chain)

        bundle, matched_scenario = self._build_bundle(
            req,
            address,
            chain,
            case_ref,
            scenario_id,
            open_result.proposed_labels,
            open_osint_mentions=[m.to_dict() for m in open_result.mentions],
        )
        engine = OSINTFusionEngine(chain_adapters=adapters, label_cache=self._label_cache)
        with span("finskalp.fusion"):
            fusion = await engine.fuse(bundle)
        self._last_fusion = fusion
        fusion_report = self._regulator.build(
            case_ref=case_ref,
            scenario_title_ru=matched_scenario.title_ru if matched_scenario else f"Расследование {address[:12]}…",
            fusion=fusion,
            bank_feed_count=len(bundle.bank_feeds),
            control_purchase_count=len(bundle.control_purchases),
            registry_label_count=self._label_cache.count(),
        ).to_dict()

        await _phase(
            "fusion",
            _PHASES_RU[4][1],
            f"Граф: {fusion_report['evidence_graph']['nodes']} узлов, "
            f"{fusion_report['evidence_graph']['edges']} рёбер",
        )
        black = sum(1 for a in fusion.attributions if a.black_zone)
        gray = sum(1 for a in fusion.attributions if a.gray_zone)
        with span("finskalp.attribution", attributions=len(fusion.attributions)):
            pass
        await _phase(
            "attribute",
            _PHASES_RU[5][1],
            f"Атрибуций: {len(fusion.attributions)}, black={black}, gray={gray}",
        )
        with span("finskalp.detect", illegal_flow_score=fusion_report.get("illegal_flow_score")):
            pass
        await _phase(
            "detect",
            _PHASES_RU[6][1],
            f"Индекс {fusion_report['illegal_flow_score']:.0f}/100 ({fusion_report['risk_level']})",
        )

        from flowsint_crypto_compliance.demo.graph_viz_adapter import (
            ensure_investigation_graph,
            evidence_graph_to_viz,
        )
        from flowsint_crypto_compliance.detection.findings import IllegalFlowFinding

        parsed_findings = [
            IllegalFlowFinding(
                severity=f.get("severity", "medium"),
                code=f.get("code", ""),
                title_ru=f.get("title_ru", ""),
                description_ru=f.get("description_ru", ""),
                addresses=f.get("addresses") or [],
                evidence=f.get("evidence"),
                confidence=f.get("confidence", 0.5),
            )
            for f in (fusion_report.get("findings") or [])
        ]
        evidence_viz = evidence_graph_to_viz(fusion.graph, parsed_findings)
        merged_graph = ensure_investigation_graph(
            address=address,
            chain=chain.value,
            live_fusion=live_fusion,
            onchain=onchain,
            evidence_graph_viz=evidence_viz,
        )
        if is_combat_mode() and merged_graph.get("nodes"):
            live_fusion = merged_graph

        if is_combat_mode() and merged_graph.get("nodes"):
            from flowsint_crypto_compliance.attribution.attribution_engine import AttributionResult
            from flowsint_crypto_compliance.reporting.graph_normalize import normalize_graph_for_ui

            attr_dict = (screening.get("onchain_summary") or {}).get("attribution") or {}
            attr_result = AttributionResult.from_dict(attr_dict)
            merged_graph = normalize_graph_for_ui(merged_graph)
            merged_graph = self._attribution.enrich_graph(merged_graph, attr_result)
            from flowsint_crypto_compliance.reporting.graph_top_tier import enrich_investigation_graph

            merged_graph = enrich_investigation_graph(
                merged_graph,
                root_address=address,
                screening=screening,
            )
            live_fusion = merged_graph

        from flowsint_crypto_compliance.reporting.forensic_builder import (
            build_forensic_report_v2,
            resolve_priority_lead_live,
        )

        attr_payload = (screening.get("onchain_summary") or {}).get("attribution") or {}
        from flowsint_crypto_compliance.attribution.attribution_engine import AttributionResult

        attribution_result = AttributionResult.from_dict(attr_payload)
        if attr_payload.get("exposure"):
            from flowsint_crypto_compliance.engine.exposure_engine import ExposureResult

            attribution_result.exposure = ExposureResult(**{
                k: v for k, v in attr_payload["exposure"].items()
                if k in ExposureResult.__dataclass_fields__
            })

        evidence_sources = {
            "trongrid_transfers": onchain,
            "attribution_snapshot": attr_payload,
            "sanctions_check": attr_payload.get("sanctions_hits"),
            "fusion_graph": live_fusion or merged_graph,
            "onchain_verification": {
                "address": address,
                "chain": chain.value,
                "inbound": onchain.get("inbound_count"),
                "outbound": onchain.get("outbound_count"),
                "verified_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        address_report = self._reporter.build_address_report(
            investigation_id=investigation_id,
            case_ref=case_ref,
            screening=screening,
            fusion_report=fusion_report,
            notes=req.notes,
            open_osint=open_dict,
        )
        graph_section = None
        if live_fusion:
            from flowsint_crypto_compliance.reporting.graph_report import graph_section_for_report

            graph_section = graph_section_for_report(live_fusion, investigation_id=investigation_id)

        onchain_for_lead = screening.get("onchain_summary") or {}
        outbound_n = onchain_for_lead.get("outbound_count", 0)
        gross_out = float(
            onchain_for_lead.get("outbound_amount")
            or (attr_payload.get("exposure") or {}).get("total_outbound")
            or 0
        )
        priority_lead = await resolve_priority_lead_live(
            subject_address=address,
            chain=chain.value,
            onchain=onchain_for_lead,
            outbound_n=outbound_n,
            gross_out=gross_out,
        )

        forensic_report = build_forensic_report_v2(
            investigation_id=investigation_id,
            case_ref=case_ref,
            address=address,
            chain=chain.value,
            screening=screening,
            attribution=attribution_result,
            fusion_report=fusion_report,
            fusion_graph=live_fusion,
            graph_section=graph_section,
            evidence_sources=evidence_sources,
            notes=req.notes,
            priority_lead=priority_lead,
            open_osint=open_dict,
        )
        from flowsint_crypto_compliance.reporting.finskalp_report import _mentions_section

        forensic_report["open_osint"] = open_dict
        forensic_report["mentions_internet"] = _mentions_section(open_dict)
        if req.tx_hash:
            forensic_report["tx_hash"] = req.tx_hash

        with span("finskalp.reports"):
            volumetric_report = self._volumetric.build(
                investigation_id=investigation_id,
                case_ref=case_ref,
                address=address,
                chain=chain.value,
                screening=screening,
                fusion_report=fusion_report,
                fusion=fusion,
                open_osint=open_dict,
                forensic_report=forensic_report,
                notes=req.notes,
            )
            seizure_report = self._seizure.build(
                investigation_id=investigation_id,
                case_ref=case_ref,
                address=address,
                chain=chain.value,
                screening=screening,
                fusion_report=fusion_report,
                open_osint=open_dict,
                notes=req.notes,
            )
            sar_report = self._sar.build(
                investigation_id=investigation_id,
                case_ref=case_ref,
                address=address,
                chain=chain.value,
                screening=screening,
                fusion_report=fusion_report,
                forensic_report=forensic_report,
                open_osint=open_dict,
                subject_id=req.subject_id,
                bank_name=req.bank_name,
                bank_reference=req.bank_reference,
                amount=req.amount,
                currency=req.currency,
                tx_hash=req.tx_hash,
                notes=req.notes,
                investigation_id_for_urls=investigation_id,
            )
        await _phase(
            "report",
            _PHASES_RU[7][1],
            f"Отчёты: address, forensic, SAR, объёмный ({volumetric_report['volume_stats']['pages_estimate']} стр.), изъятие",
        )

        attachments = [
            {
                "type": "sar",
                "title_ru": "SAR · структурированный отчёт (115-ФЗ)",
                "url": f"/api/finskalp/report/{investigation_id}/pdf?type=sar",
            },
            {
                "type": "address",
                "title_ru": "Скрининг адреса (ФинСкальп)",
                "url": f"/api/finskalp/report/{investigation_id}/pdf?type=address",
            },
            {
                "type": "forensic",
                "title_ru": "Форензика · полный отчёт (ФинСкальп)",
                "url": f"/api/finskalp/report/{investigation_id}/pdf?type=forensic",
            },
            {
                "type": "volumetric",
                "title_ru": "Объёмный отчёт · полный пакет доказательств",
                "url": f"/api/finskalp/report/{investigation_id}/pdf?type=volumetric",
            },
            {
                "type": "seizure",
                "title_ru": "Материалы для изъятия активов",
                "url": f"/api/finskalp/report/{investigation_id}/pdf?type=seizure",
            },
        ]
        if req.tx_hash:
            attachments.append(
                {
                    "type": "transaction",
                    "title_ru": "Анализ транзакции (ФинСкальп)",
                    "url": f"/api/finskalp/report/{investigation_id}/pdf?type=transaction",
                }
            )

        duration_ms = int((time.perf_counter() - t0) * 1000)
        pipeline_chain = await self._emit_v2_investigation_events(
            investigation_id=investigation_id,
            case_ref=case_ref,
            address=address,
            chain=chain.value,
            screening=screening,
            open_dict=open_dict,
            correlation_id=correlation_id,
        )
        return FinSkalpInvestigationResult(
            investigation_id=investigation_id,
            case_ref=case_ref,
            address=address,
            chain=chain,
            duration_ms=duration_ms,
            phases=phases,
            screening=screening,
            fusion_report=fusion_report,
            address_report=address_report,
            forensic_report=forensic_report,
            open_osint=open_dict,
            live_fusion=live_fusion,
            scenario_id=scenario_id,
            volumetric_report=volumetric_report,
            sar_report=sar_report,
            seizure_report=seizure_report,
            attachments=attachments,
        )

    async def _emit_v2_investigation_events(
        self,
        *,
        investigation_id: str,
        case_ref: str,
        address: str,
        chain: str,
        screening: dict[str, Any],
        open_dict: dict[str, Any],
        correlation_id: str | None,
    ) -> dict[str, Any] | None:
        """RFC-0003 Appendix A: full pipeline chain + platform events."""
        try:
            import os
            import uuid as _uuid

            from flowsint_crypto_compliance.platform.v2.events import EventType, PlatformEvent
            from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus
            from flowsint_crypto_compliance.platform.v2.pipeline_chain import get_pipeline_chain_orchestrator

            tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
            tenant_id = _uuid.UUID(tenant_raw)
            inv_id = _uuid.UUID(investigation_id)
            mentions = open_dict.get("mentions") or []

            chain_result = await get_pipeline_chain_orchestrator().run_investigation_chain(
                tenant_id=tenant_id,
                investigation_id=inv_id,
                case_ref=case_ref,
                address=address,
                chain=chain,
                screening=screening,
                mentions=mentions if isinstance(mentions, list) else [],
                correlation_id=correlation_id,
                actor="finskalp.investigator",
            )

            bus = get_platform_event_bus()
            bus.publish(
                PlatformEvent(
                    event_type=EventType.CASE_OPENED,
                    source="finskalp.investigator",
                    tenant_id=tenant_id,
                    investigation_id=inv_id,
                    correlation_id=correlation_id,
                    payload={
                        "case_ref": case_ref,
                        "address": address,
                        "chain": chain,
                        "pipeline_chain": chain_result.to_dict(),
                    },
                )
            )
            bus.publish(
                PlatformEvent(
                    event_type=EventType.RISK_UPDATED,
                    source="finskalp.investigator",
                    tenant_id=tenant_id,
                    investigation_id=inv_id,
                    correlation_id=correlation_id,
                    payload={
                        "case_ref": case_ref,
                        "score": screening.get("risk_score"),
                        "level": screening.get("risk_level"),
                    },
                )
            )
            return chain_result.to_dict()
        except Exception:
            return None

    def _build_adapters(
        self,
        chain: Chain,
        address: str,
        scenario_id: str | None,
    ) -> dict[Chain, Any]:
        """Live chain APIs in combat mode; demo fixtures only when COMPLIANCE_COMBAT_MODE=0."""
        if is_combat_mode():
            adapters: dict[Chain, Any] = {}
            if _use_live_chain_adapter(address, chain, scenario_id):
                try:
                    adapters[chain] = get_chain_adapter(chain)
                except Exception:
                    pass
            if chain not in adapters:
                adapters[chain] = InMemoryChainAdapter(chain, [])
            return adapters
        adapters = dict(get_demo_adapters(scenario_id))
        if _use_live_chain_adapter(address, chain, scenario_id):
            try:
                adapters[chain] = get_chain_adapter(chain)
            except Exception:
                pass
        if chain not in adapters:
            adapters[chain] = InMemoryChainAdapter(chain, [])
        return adapters

    def _build_bundle(
        self,
        req: FinSkalpInvestigationRequest,
        address: str,
        chain: Chain,
        case_ref: str,
        scenario_id: str | None,
        open_labels: list | None = None,
        open_osint_mentions: list[dict[str, Any]] | None = None,
    ) -> tuple[InvestigationBundle, Any | None]:
        matched = None
        if scenario_id and not is_combat_mode():
            try:
                matched = get_scenario(scenario_id)
            except KeyError:
                matched = None
        elif scenario_id and is_combat_mode():
            scenario_id = None

        bank_feeds: list[BankRegulatorFeed] = []
        licensed: list[LicensedPlatformEvent] = []
        control = []
        registry = []

        if matched:
            bank_feeds = list(matched.bank_feeds)
            licensed = list(matched.licensed_events)
            control = list(matched.control_purchases)
            registry = list(matched.registry_labels)
            for label in registry:
                self._label_cache.put(label)

        if open_labels:
            for label in open_labels:
                registry.append(label)
                self._label_cache.put(label)

        if req.bank_reference or req.amount or req.bank_name:
            bank_feeds.append(
                BankRegulatorFeed(
                    feed_id=req.bank_reference or f"STR-{case_ref}",
                    bank_name=req.bank_name or "Банк (ввод аналитика)",
                    alert_type="STR",
                    region=req.region,
                    currency=req.currency or "RUB",
                    amount=req.amount,
                    payment_reference=req.bank_reference,
                    linked_crypto_address=address,
                    linked_chain=chain,
                    subject_id=req.subject_id,
                    case_id=case_ref,
                )
            )

        if not licensed and not is_combat_mode():
            licensed.append(
                LicensedPlatformEvent(
                    event_id=f"FS-LIC-{case_ref}",
                    platform_name="FinSkalp_target",
                    region=req.region,
                    chain=chain,
                    address=address,
                    direction="deposit",
                    asset="USDT" if chain == Chain.TRON else None,
                )
            )

        fiat = [bank_feed_to_fiat_event(b) for b in bank_feeds]
        return (
            InvestigationBundle(
                case_id=case_ref,
                bank_feeds=bank_feeds,
                fiat_events=fiat,
                licensed_events=licensed,
                control_purchases=control,
                registry_labels=registry,
                open_osint_mentions=open_osint_mentions or [],
                open_osint_address=address,
                open_osint_chain=chain,
            ),
            matched,
        )


def _extract_counterparties(screening: dict[str, Any]) -> list[str]:
    """Counterparty hints from on-chain summary if present."""
    summary = screening.get("onchain_summary") or {}
    cps = summary.get("counterparty_addresses") or []
    if isinstance(cps, list):
        return [str(c) for c in cps if c]
    return []


def match_scenario_for_address(address: str, chain: Chain) -> str | None:
    norm = address.lower() if chain == Chain.ETH else address
    for sid, scenario in SCENARIOS.items():
        for feed in scenario.bank_feeds:
            linked = feed.linked_crypto_address
            if linked and linked in (address, norm):
                return sid
        for cp in scenario.control_purchases:
            if address in (cp.target_address, cp.source_address or ""):
                return sid
        for event in scenario.licensed_events:
            if event.address == address or (chain == Chain.ETH and event.address.lower() == norm):
                return sid
        for label in scenario.registry_labels:
            if label.address == address or (chain == Chain.ETH and label.address.lower() == norm):
                return sid
    for sid, per_chain in DEMO_TRANSFERS.items():
        for txs in per_chain.values():
            for tx in txs:
                if address in (tx.source, tx.target):
                    return sid
    return None


def _use_live_chain_adapter(address: str, chain: Chain, scenario_id: str | None) -> bool:
    if is_combat_mode():
        return is_live_address(address, chain.value)
    if scenario_id or match_scenario_for_address(address, chain):
        return False
    if chain == Chain.TRON:
        return len(address) == 34 and address.startswith("T") and "_" not in address
    if chain == Chain.ETH:
        return address.startswith("0x") and len(address) >= 42
    if chain == Chain.BTC:
        return address.startswith(("bc1", "1", "3"))
    return False


async def _prefetch_adapters_to_memory(
    adapters: dict[Any, Any],
    chain: Chain,
    address: str,
    *,
    limit: int,
) -> None:
    """Один live-запрос к обозревателю → дальше только in-memory (без повторных TronGrid)."""
    adapter = adapters.get(chain)
    if adapter is None or isinstance(adapter, InMemoryChainAdapter):
        return
    try:
        extra_txs = await asyncio.wait_for(
            _fetch_neighborhood_txs(adapter, address, limit=max(limit, 200)),
            timeout=25.0,
        )
    except (asyncio.TimeoutError, Exception):
        extra_txs = []
    adapters[chain] = InMemoryChainAdapter(chain, extra_txs)


async def _fetch_neighborhood_txs(
    adapter: Any, address: str, *, limit: int = 80
) -> list[OnChainTransfer]:
    if adapter is None:
        return []
    try:
        nb = await adapter.get_neighborhood(address, limit=limit)
        seen: set[str] = set()
        out: list[OnChainTransfer] = []
        for tx in list(nb.inbound) + list(nb.outbound):
            if tx.tx_hash not in seen:
                seen.add(tx.tx_hash)
                out.append(tx)
        return out
    except Exception:
        return []
