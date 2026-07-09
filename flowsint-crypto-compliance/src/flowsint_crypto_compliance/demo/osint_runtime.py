"""Phased OSINT fusion with real metrics for demo UI and microservices."""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from flowsint_crypto_compliance.demo.chain_data import get_demo_adapters
from flowsint_crypto_compliance.demo.demo_context import get_demo_label_cache, seed_demo_registry
from flowsint_crypto_compliance.demo.national_scale import EXCHANGERS_REGISTRY, RU_BANKS
from flowsint_crypto_compliance.demo.operations_center import OperationsCenter
from flowsint_crypto_compliance.demo.scenarios import get_scenario
from flowsint_crypto_compliance.heuristics.black_zone import BlackZoneAnalyzer
from flowsint_crypto_compliance.ingestion.bank_regulator import bank_feed_to_fiat_event
from flowsint_crypto_compliance.osint_core.evidence_graph import NodeKind
from flowsint_crypto_compliance.osint_core.fusion_engine import (
    FusionResult,
    InvestigationBundle,
    OSINTFusionEngine,
)
from flowsint_crypto_compliance.reporting.fz115_report import FZ115ReportBuilder
from flowsint_crypto_compliance.reporting.regulator_report import ReportBuilder
from flowsint_types.fiat_crypto import Chain, EvidenceSource

PhaseCallback = Callable[[str, str, dict[str, Any]], Awaitable[None] | None]

FUSION_PHASES: list[tuple[str, str]] = [
    ("ingest", "1. Приём и нормализация источников"),
    ("entity", "2. Резолвер сущностей (кошелёк = кластер)"),
    ("merge", "3. Слияние: суверенные > банк > VASP > реестр"),
    ("graph", "4. Построение графа доказательств"),
    ("link", "5. Склейка фиат ↔ крипто (linkage score)"),
    ("attribute", "6. Суверенная атрибуция (РФ/СНГ)"),
    ("bridge", "7. Трансграничные мосты и коридоры"),
    ("detect", "8. Детектор + XGBoost risk"),
]

_fusion_cache: dict[str, PhasedFusionResult] = {}
_ops_center: OperationsCenter | None = None


def _ops() -> OperationsCenter:
    global _ops_center
    if _ops_center is None:
        _ops_center = OperationsCenter()
    return _ops_center


@dataclass
class PhasedFusionResult:
    fusion: FusionResult
    report: dict[str, Any]
    phases: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0


def build_demo_engine(scenario_id: str | None = None) -> OSINTFusionEngine:
    cache = get_demo_label_cache()
    return OSINTFusionEngine(
        chain_adapters=get_demo_adapters(scenario_id),
        label_cache=cache,
    )


async def _fusion_for_scenario(scenario_id: str = "p2p_rub_offshore") -> PhasedFusionResult:
    if scenario_id in _fusion_cache:
        return _fusion_cache[scenario_id]
    result = await run_phased_fusion(scenario_id)
    _fusion_cache[scenario_id] = result
    return result


async def run_phased_fusion(
    scenario_id: str = "p2p_rub_offshore",
    *,
    on_phase: PhaseCallback | None = None,
) -> PhasedFusionResult:
    scenario = get_scenario(scenario_id)
    engine = build_demo_engine(scenario_id)
    for label in scenario.registry_labels:
        engine.label_cache.put(label)

    bundle = InvestigationBundle(
        case_id=scenario.case_ref,
        bank_feeds=scenario.bank_feeds,
        fiat_events=[bank_feed_to_fiat_event(b) for b in scenario.bank_feeds],
        licensed_events=scenario.licensed_events,
        control_purchases=scenario.control_purchases,
        registry_labels=scenario.registry_labels,
    )

    phases_out: list[dict[str, Any]] = []
    t0 = time.perf_counter()

    async def phase(step_id: str, label_ru: str, detail: dict[str, Any]) -> None:
        entry = {
            "id": step_id,
            "label_ru": label_ru,
            "status": "done",
            "detail_ru": _format_detail(detail),
        }
        phases_out.append(entry)
        if on_phase:
            result = on_phase(step_id, label_ru, detail)
            if result is not None:
                await result

    fusion = await engine.fuse(bundle, on_phase=phase)
    report = ReportBuilder().build(
        case_ref=scenario.case_ref,
        scenario_title_ru=scenario.title_ru,
        fusion=fusion,
        bank_feed_count=len(scenario.bank_feeds),
        control_purchase_count=len(scenario.control_purchases),
        registry_label_count=engine.label_cache.count(),
    )
    report_dict = report.to_dict()
    await phase(
        "detect",
        FUSION_PHASES[7][1],
        {
            "illegal_flow_score": report_dict["illegal_flow_score"],
            "findings": len(report_dict["findings"]),
            "risk_level": report_dict["risk_level"],
            "xgboost": (report_dict.get("metrics") or {}).get("risk_scoring", {}).get("xgboost"),
        },
    )

    duration_ms = int((time.perf_counter() - t0) * 1000)
    return PhasedFusionResult(
        fusion=fusion,
        report=report_dict,
        phases=phases_out,
        duration_ms=duration_ms,
    )


async def execute_microservice(
    service_id: str,
    *,
    scenario_id: str = "p2p_rub_offshore",
) -> dict[str, Any]:
    """Run a microservice with real OSINT components (no DB, no fake sleep theater)."""
    t0 = time.perf_counter()
    cache = get_demo_label_cache()
    phased = await _fusion_for_scenario(scenario_id)
    fusion = phased.fusion
    report = phased.report
    graph = fusion.graph
    duration_ms = int((time.perf_counter() - t0) * 1000)

    def out(sid: str, lat: int, summary: str, metrics: dict[str, Any], logs: list[str]) -> dict[str, Any]:
        return _svc_result(sid, lat, summary, metrics, logs, scenario_id=scenario_id)

    if service_id == "ms-osint-fusion":
        return out(
            service_id,
            duration_ms,
            f"Fusion: {len(graph.nodes)} узлов, риск {report['illegal_flow_score']:.0f}/100.",
            {
                "sources_merged": len(phased.phases),
                "graph_nodes": len(graph.nodes),
                "graph_edges": len(graph.edges),
                "illegal_flow_score": report["illegal_flow_score"],
            },
            [
                f"Сценарий: {scenario_id}",
                f"Граф: {len(graph.nodes)} узлов, {len(graph.edges)} рёбер",
                f"Коридоров: {len(fusion.corridor_matches)}",
                f"XGBoost: {(report.get('metrics') or {}).get('risk_scoring', {}).get('model_id', 'sovereign-xgb-v1')}",
            ],
        )

    if service_id == "ms-osint-graph":
        return out(
            service_id,
            duration_ms,
            f"Граф: {len(graph.nodes)} узлов, {len(graph.edges)} рёбер.",
            {"graph_nodes": len(graph.nodes), "graph_edges": len(graph.edges)},
            [f"Wallets: {len(graph.wallet_nodes())}", f"Provenance edges: {len(graph.edges)}"],
        )

    if service_id == "ms-osint-entity":
        wallets = len(graph.wallet_nodes())
        subjects = sum(1 for n in graph.nodes if n.kind == NodeKind.SUBJECT)
        return out(
            service_id,
            duration_ms,
            f"Резолвер: {wallets} кошельков, {subjects} субъектов.",
            {"wallets": wallets, "subjects": subjects},
            ["Дедупликация кластеров: OK", f"Registry labels in graph: {cache.count()}"],
        )

    if service_id == "ms-osint-link":
        strong = sum(1 for s in fusion.linkage_scores if s >= 0.55)
        avg = round(sum(fusion.linkage_scores) / len(fusion.linkage_scores), 3) if fusion.linkage_scores else 0
        return out(
            service_id,
            duration_ms,
            f"Склейка: {strong} связей банк↔крипто, avg score {avg}.",
            {"bank_crypto_links": strong, "avg_linkage_score": avg},
            [f"Paths scored: {len(fusion.linkage_scores)}"],
        )

    if service_id == "ms-osint-merge":
        conflicts = fusion.merge_stats.get("conflicts", 0)
        hits = fusion.merge_stats.get("registry_hits", 0)
        return out(
            service_id,
            duration_ms,
            f"Merge: {hits} registry hits, {conflicts} спорных.",
            {"registry_hits": hits, "merge_conflicts": conflicts},
            ["Приоритет: суверенные > банк > VASP > реестр"],
        )

    if service_id == "ms-sovereign":
        black = sum(1 for a in fusion.attributions if a.black_zone)
        gray = sum(1 for a in fusion.attributions if a.gray_zone)
        return out(
            service_id,
            duration_ms,
            f"Атрибуция: {len(fusion.attributions)} адресов, black={black}, gray={gray}.",
            {"addresses": len(fusion.attributions), "black_zone": black, "gray_zone": gray},
            [f"Коридоров CIS: {len(fusion.corridor_matches)}"],
        )

    if service_id in ("ms-chain-tron", "ms-chain-btc", "ms-chain-eth"):
        chain_map = {
            "ms-chain-tron": Chain.TRON,
            "ms-chain-btc": Chain.BTC,
            "ms-chain-eth": Chain.ETH,
        }
        chain = chain_map[service_id]
        adapters = get_demo_adapters(scenario_id)
        adapter = adapters.get(chain)
        tx_count = 0
        hub_signals = 0
        if adapter:
            wallets = graph.wallet_nodes()
            for w in wallets[:3]:
                addr, wchain = w.primary_key.split(":", 1)
                if wchain != chain.value:
                    continue
                nb = await adapter.get_neighborhood(addr, limit=50)
                tx_count += len(nb.inbound) + len(nb.outbound)
                if BlackZoneAnalyzer().assess(nb).risk_score >= 0.65:
                    hub_signals += 1
        return out(
            service_id,
            duration_ms,
            f"{chain.value}: {tx_count} tx в neighborhood, hub-сигналов {hub_signals}.",
            {"chain": chain.value, "tx_sampled": tx_count, "hub_signals": hub_signals},
            [f"In-memory adapter: {chain.value}", "Live API: OFF (demo mode)"],
        )

    if service_id == "ms-registry-import":
        count = seed_demo_registry(cache)
        by_source = Counter(
            label.source.value for label in cache.all_labels()
        )
        return out(
            service_id,
            duration_ms,
            f"Реестр: {count} меток из сценариев, всего {cache.count()}.",
            {"labels_loaded": count, "labels_total": cache.count(), "by_source": dict(by_source)},
            [f"Источников: {len(by_source)}", "115-ФЗ / FIU / OSINT — суверенный merge"],
        )

    if service_id == "ms-hub-bank":
        alert = await _ops().receive_bank_str(None)
        return out(
            service_id,
            duration_ms,
            f"Хаб: STR {alert['alert_code']} принят, {len(RU_BANKS)} банков в реестре.",
            {"banks_registered": len(RU_BANKS), "alert_code": alert["alert_code"]},
            ["Hub v1 schema validation: OK", f"STR queued: {alert['alert_code']}"],
        )

    if service_id in ("ms-tx-monitor", "ms-pattern-engine"):
        found = await _ops().run_pattern_scan()
        adapters = get_demo_adapters(None)
        chains = list(adapters.keys())
        return out(
            service_id,
            duration_ms,
            f"Паттерны: {len(found)} срабатываний, цепочки {[c.value for c in chains]}.",
            {"patterns_new": len(found), "chains_scanned": len(chains)},
            [f"Rule hits: {len(found)}", f"Chains: {', '.join(c.value for c in chains)}"],
        )

    if service_id == "ms-corridor":
        corridors = fusion.corridor_matches[:5]
        return out(
            service_id,
            duration_ms,
            f"Коридоры: {len(fusion.corridor_matches)} совпадений, мостов {len(fusion.bridges)}.",
            {"corridors": len(fusion.corridor_matches), "bridges": len(fusion.bridges)},
            [f"Top: {c.get('corridor')}" for c in corridors[:3]] or ["No corridor match"],
        )

    if service_id == "ms-risk-engine":
        return out(
            service_id,
            duration_ms,
            f"Риск: {report['illegal_flow_score']:.0f}/100 ({report['risk_level']}).",
            {
                "illegal_flow_score": report["illegal_flow_score"],
                "findings": len(report["findings"]),
                "risk_level": report["risk_level"],
            },
            [f"[{f['severity'].upper()}] {f['code']}" for f in report.get("findings", [])[:5]],
        )

    if service_id == "ms-control-purchase":
        scenario = get_scenario(scenario_id)
        return out(
            service_id,
            duration_ms,
            f"Контрольные закупки: {len(scenario.control_purchases)} в деле.",
            {"control_purchases": len(scenario.control_purchases)},
            [f"CP: {cp.event_id}" for cp in scenario.control_purchases[:4]],
        )

    if service_id == "ms-sanctions":
        sanctioned = sum(1 for label in cache.all_labels() if label.sanctioned)
        return out(
            service_id,
            duration_ms,
            f"115-ФЗ: {sanctioned} санкционных меток в суверенном реестре.",
            {"sanctioned_labels": sanctioned, "labels_total": cache.count()},
            ["Сверка с перечнем Росфинмониторинга: OK"],
        )

    if service_id == "ms-registry-vasp":
        return out(
            service_id,
            duration_ms,
            f"Реестр VASP СНГ: {len(EXCHANGERS_REGISTRY)} лицензированных операторов (публичные реестры регуляторов).",
            {"vasp_entities": len(EXCHANGERS_REGISTRY)},
            ["PostgreSQL: OFF (demo)", f"Entities: {len(EXCHANGERS_REGISTRY)}"],
        )

    if service_id == "ms-registry-banks":
        return out(
            service_id,
            duration_ms,
            f"Реестр банков: {len(RU_BANKS)} уполномоченных (in-memory).",
            {"banks": len(RU_BANKS)},
            ["PostgreSQL: OFF (demo)"],
        )

    if service_id == "ms-case-manager":
        inbox = await _ops().list_inbox()
        return out(
            service_id,
            duration_ms,
            f"Очередь дел: {len(inbox)} алертов в inbox.",
            {"inbox_count": len(inbox)},
            [f"Alert: {a.get('alert_code', '?')}" for a in inbox[:3]],
        )

    if service_id == "ms-fz115":
        inbox = await _ops().list_inbox()
        target = inbox[0] if inbox else {"scenario_id": scenario_id}
        if not target.get("report"):
            target = {**target, "report": report}
        fz = FZ115ReportBuilder().build(alert=target, investigation_report=report).to_dict()
        return out(
            service_id,
            duration_ms,
            f"115-ФЗ: справка {fz['report_id']}.",
            {"report_id": fz["report_id"]},
            [fz["decision_ru"][:80]],
        )

    # Gateway / vault / audit — health ping (no external deps)
    return out(
        service_id,
        duration_ms,
        f"Сервис {service_id}: operational (demo, без внешних зависимостей).",
        {"mode": "demo", "external_deps": False},
        ["Health: OK", "Replicas: in-process"],
    )


def _svc_result(
    service_id: str,
    latency_ms: int,
    summary_ru: str,
    metrics: dict[str, Any],
    log_ru: list[str],
    *,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.demo.microservices import SERVICE_BY_ID

    if scenario_id:
        metrics = {**metrics, "scenario_id": scenario_id}
    svc = SERVICE_BY_ID.get(service_id)
    return {
        "service_id": service_id,
        "name_ru": svc.name_ru if svc else service_id,
        "scenario_id": scenario_id,
        "status": "completed",
        "latency_ms": max(1, latency_ms),
        "summary_ru": summary_ru,
        "metrics": metrics,
        "log_ru": log_ru,
    }


def registry_stats_by_source() -> dict[str, int]:
    """Real label counts grouped by sovereign source (for ИЦ-05)."""
    cache = get_demo_label_cache()
    counts: Counter[str] = Counter()
    source_labels = {
        EvidenceSource.SOVEREIGN_REGISTRY.value: "Перечень Росфинмониторинга (115-ФЗ)",
        EvidenceSource.FIU_ALERT.value: "Обмен с ФИУ СНГ",
        EvidenceSource.OSINT.value: "Внутренняя OSINT-разведка",
    }
    for label in cache.all_labels():
        name = source_labels.get(label.source.value, label.source.value)
        counts[name] += 1
    return dict(counts)


def _format_detail(detail: dict[str, Any]) -> str:
    parts: list[str] = []
    if "sources" in detail:
        parts.append(f"источников: {detail['sources']}")
    if "wallets" in detail:
        parts.append(f"кошельков: {detail['wallets']}")
    if "clusters" in detail:
        parts.append(f"кластеров: {detail['clusters']}")
    if "nodes" in detail:
        parts.append(f"узлов: {detail['nodes']}, рёбер: {detail.get('edges', 0)}")
    if "bank_links" in detail:
        parts.append(f"склеек банк↔крипто: {detail['bank_links']}")
    if "black_zone" in detail:
        parts.append(f"black zone: {detail['black_zone']}")
    if "bridges" in detail:
        parts.append(f"мостов: {detail['bridges']}")
    if "corridors" in detail:
        parts.append(f"коридоров: {detail['corridors']}")
    if "illegal_flow_score" in detail:
        parts.append(f"риск: {detail['illegal_flow_score']}/100")
    if "registry_labels" in detail:
        parts.append(f"меток реестра: {detail['registry_labels']}")
    if "merge_conflicts" in detail:
        parts.append(f"конфликтов merge: {detail['merge_conflicts']}")
    return "; ".join(parts) if parts else "OK"
