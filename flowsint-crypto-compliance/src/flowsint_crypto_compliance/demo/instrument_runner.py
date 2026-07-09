"""
Автономный запуск каждого инструмента ИЦ-01…ИЦ-08 вне цепочки расследования.
"""

from __future__ import annotations

import time
from typing import Any

from flowsint_crypto_compliance.demo.chain_data import ALL_BY_CHAIN
from flowsint_crypto_compliance.demo.demo_context import get_demo_chain_adapters, get_demo_label_cache
from flowsint_crypto_compliance.demo.national_scale import (
    NATIONAL_METRICS,
    RU_BANKS,
    EXCHANGERS_REGISTRY,
    cis_coverage,
    get_dashboard,
)
from flowsint_crypto_compliance.demo.operations_center import OperationsCenter
from flowsint_crypto_compliance.demo.runner import RegulatorDemoRunner
from flowsint_crypto_compliance.demo.enterprise_platform import MODULE_BY_IC
from flowsint_crypto_compliance.demo.alert_registry import get_scenario_meta
from flowsint_crypto_compliance.demo.scenarios import get_scenario
from flowsint_crypto_compliance.reporting.fz115_report import FZ115ReportBuilder
from flowsint_crypto_compliance.services.finskalp_investigator import (
    FinSkalpInvestigationRequest,
    FinSkalpInvestigator,
)
from flowsint_crypto_compliance.cis.coverage import CIS_CORRIDORS
from flowsint_types.fiat_crypto import Chain

CAPABILITY_TAG: dict[str, str] = {
    ic: mod.capability_tag_ru for ic, mod in MODULE_BY_IC.items()
}


class InstrumentRunner:
    def __init__(self, center: OperationsCenter) -> None:
        self._center = center
        self._demo = RegulatorDemoRunner()
        self._fz115 = FZ115ReportBuilder()
        self._finskalp = FinSkalpInvestigator()
        self._last_runs: dict[str, dict[str, Any]] = {}

    def last_run(self, code: str) -> dict[str, Any] | None:
        return self._last_runs.get(code)

    async def run(
        self,
        code: str,
        *,
        scenario_id: str | None = None,
        alert_id: str | None = None,
        address: str | None = None,
        chain: str | None = None,
        bank_reference: str | None = None,
        amount: float | None = None,
    ) -> dict[str, Any]:
        handlers = {
            "ИЦ-01": self._run_ic01,
            "ИЦ-02": self._run_ic02,
            "ИЦ-03": self._run_ic03,
            "ИЦ-04": self._run_ic04,
            "ИЦ-05": self._run_ic05,
            "ИЦ-06": self._run_ic06,
            "ИЦ-07": self._run_ic07,
            "ИЦ-08": self._run_ic08,
        }
        if code not in handlers:
            raise KeyError(f"Unknown instrument: {code}")

        t0 = time.perf_counter()
        result = await handlers[code](
            scenario_id=scenario_id,
            alert_id=alert_id,
            address=address,
            chain=chain,
            bank_reference=bank_reference,
            amount=amount,
        )
        duration_ms = int((time.perf_counter() - t0) * 1000)

        payload = {
            "instrument_code": code,
            "capability_ru": CAPABILITY_TAG.get(code, ""),
            "status": "completed",
            "duration_ms": duration_ms,
            **result,
        }
        self._last_runs[code] = payload
        return payload

    async def _run_ic01(self, **_: Any) -> dict[str, Any]:
        alert = await self._center.receive_bank_str(None)
        online = [b for b in RU_BANKS if True][:97]
        return {
            "summary_ru": (
                f"Синхронизация хаба: {NATIONAL_METRICS['banks_online']}/"
                f"{NATIONAL_METRICS['banks_total']} банков онлайн. "
                f"Принято новое STR: {alert['alert_code']}."
            ),
            "metrics": {
                "banks_online": NATIONAL_METRICS["banks_online"],
                "messages_24h": get_dashboard()["hub_messages_24h"],
                "validated_ok": 18412,
                "validated_fail": 8,
            },
            "output": {
                "new_alert": alert,
                "sample_banks": [{"bic": b["bic"], "name": b["name"]} for b in online[:5]],
            },
            "log_lines": [
                "Hub v1 schema validation: OK",
                f"STR queued: {alert['alert_code']}",
                f"Sources: {len(RU_BANKS)} registered banks",
            ],
        }

    async def _run_ic02(self, **_: Any) -> dict[str, Any]:
        found = await self._center.run_pattern_scan()
        adapters = get_demo_chain_adapters()
        return {
            "summary_ru": (
                f"Скан on-chain завершён: {len(found)} паттернов, "
                f"цепочки: {', '.join(c.value for c in adapters)}."
            ),
            "metrics": {
                "patterns_new": len(found),
                "chains_scanned": len(adapters),
                "wallets_in_graph": sum(len(txs) for txs in ALL_BY_CHAIN.values()),
            },
            "output": {"alerts": found, "rules_active": len(found)},
            "log_lines": [
                f"Chains: {', '.join(c.value for c in adapters)}",
                f"Hits: {len(found)}",
            ],
        }

    async def _finskalp_payload(self, **kwargs: Any) -> dict[str, Any]:
        address = kwargs.get("address")
        if not address:
            return {}
        chain_val = kwargs.get("chain")
        chain = Chain(chain_val.lower()) if chain_val else None
        inv = await self._finskalp.investigate(
            FinSkalpInvestigationRequest(
                address=address.strip(),
                chain=chain,
                scenario_id=kwargs.get("scenario_id"),
                bank_reference=kwargs.get("bank_reference"),
                amount=kwargs.get("amount"),
            )
        )
        d = inv.to_dict()
        return {
            "summary_ru": (
                f"ФинСкальп: {d['address'][:12]}… · риск {d['risk_score']:.0f}/100 · "
                f"граф {d['fusion_report']['evidence_graph']['nodes']} узлов"
            ),
            "metrics": {
                "risk_score": d["risk_score"],
                "graph_nodes": d["fusion_report"]["evidence_graph"]["nodes"],
                "duration_ms": d["duration_ms"],
            },
            "output": {
                "investigation_id": d["investigation_id"],
                "attachments": d["attachments"],
                "phases": d["phases"],
            },
            "log_lines": [p["detail_ru"] for p in d["phases"]],
        }

    async def _run_ic03(self, scenario_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
        if kwargs.get("address"):
            return await self._finskalp_payload(**kwargs)
        sid = scenario_id or "p2p_rub_offshore"
        report = await self._demo.run(sid)
        d = report.to_dict()
        return {
            "summary_ru": (
                f"Fusion graph: {d['evidence_graph']['nodes']} узлов, "
                f"индекс риска {d['illegal_flow_score']:.0f}/100."
            ),
            "metrics": d["metrics"],
            "output": {
                "case_ref": d["case_ref"],
                "risk_level": d["risk_level"],
                "findings_count": len(d["findings"]),
                "graph": d["evidence_graph"],
            },
            "log_lines": [
                "Bank feeds + VASP + control purchases merged",
                "Domestic evidence priority: ON",
                f"Scenario: {sid}",
            ],
        }

    async def _run_ic04(self, scenario_id: str | None = None, **_: Any) -> dict[str, Any]:
        sid = scenario_id or "sbp_gray_hub"
        report = await self._demo.run(sid)
        attrs = report.to_dict().get("attributions", [])
        black = sum(1 for a in attrs if a.get("black_zone"))
        gray = sum(1 for a in attrs if a.get("gray_zone"))
        return {
            "summary_ru": (
                f"Суверенная атрибуция: {len(attrs)} адресов, "
                f"чёрная зона {black}, серая {gray}. Без иностранного KYT как единственного источника."
            ),
            "metrics": {
                "addresses": len(attrs),
                "black_zone": black,
                "gray_zone": gray,
                "cis_regions": len(cis_coverage()),
            },
            "output": {
                "top_attributions": attrs[:5],
                "exchangers_in_registry": NATIONAL_METRICS["vasp_otc_flagged"],
            },
            "log_lines": [
                "CIS sovereign model loaded",
                "Behavioral heuristics applied",
                f"Registry cross-ref: {len(EXCHANGERS_REGISTRY)} OTC entities",
            ],
        }

    async def _run_ic05(self, **_: Any) -> dict[str, Any]:
        from flowsint_crypto_compliance.demo.osint_runtime import registry_stats_by_source

        labels_by_source = registry_stats_by_source()
        cache = get_demo_label_cache()
        sanctioned = sum(1 for label in cache.all_labels() if label.sanctioned)
        return {
            "summary_ru": (
                f"Сверка с суверенным реестром: {cache.count()} меток, "
                f"{len(labels_by_source)} источников. Санкции 115-ФЗ: {sanctioned}."
            ),
            "metrics": {
                "labels_total": cache.count(),
                "sources": len(labels_by_source),
                "sanctioned_115fz": sanctioned,
            },
            "output": {"by_source": labels_by_source, "chains": ["BTC", "ETH", "TRON"]},
            "log_lines": [
                f"Перечень Росфинмониторинга: {labels_by_source.get('Перечень Росфинмониторинга (115-ФЗ)', 0)} меток",
                f"Внутренняя OSINT: {labels_by_source.get('Внутренняя OSINT-разведка', 0)} меток",
                "Merge engine: суверенный источник — приоритетный",
            ],
        }

    async def _run_ic06(self, scenario_id: str | None = None, **_: Any) -> dict[str, Any]:
        sid = scenario_id or "cis_transit_kz"
        report = await self._demo.run(sid)
        bridges = report.to_dict().get("bridges", [])
        corridors = [list(c) for c in CIS_CORRIDORS[:6]]
        return {
            "summary_ru": (
                f"Анализ коридоров: {len(bridges)} мостов, "
                f"{NATIONAL_METRICS['cis_corridors_active']} активных маршрутов РФ/СНГ."
            ),
            "metrics": {
                "bridges": len(bridges),
                "corridors_active": NATIONAL_METRICS["cis_corridors_active"],
                "jurisdictions": NATIONAL_METRICS["cis_jurisdictions"],
            },
            "output": {
                "corridors": corridors,
                "bridges": bridges[:5],
                "cis": cis_coverage(),
            },
            "log_lines": [
                "RU→KZ→TR corridor: elevated",
                "RU→DO off-ramp: monitored",
                f"Scenario anchor: {sid}",
            ],
        }

    async def _run_ic07(self, scenario_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
        if kwargs.get("address"):
            payload = await self._finskalp_payload(**kwargs)
            d = payload.get("output") or {}
            return {
                **payload,
                "summary_ru": payload["summary_ru"].replace("ФинСкальп:", "Детектор ФинСкальп:"),
            }
        sid = scenario_id or "sbp_gray_hub"
        report = await self._demo.run(sid)
        d = report.to_dict()
        return {
            "summary_ru": (
                f"Детектор: индекс {d['illegal_flow_score']:.0f}/100 ({d['risk_level']}), "
                f"{len(d['findings'])} индикаторов нелегального движения ценностей."
            ),
            "metrics": {"score": d["illegal_flow_score"], "risk": d["risk_level"]},
            "output": {"findings": d["findings"]},
            "log_lines": [f"[{f['severity'].upper()}] {f['code']}" for f in d["findings"][:6]],
        }

    async def _run_ic08(self, alert_id: str | None = None, **_: Any) -> dict[str, Any]:
        target: dict[str, Any] | None = None
        if alert_id:
            try:
                target = await self._center.get_alert(alert_id)
            except KeyError:
                pass
        if not target:
            inbox = await self._center.list_inbox()
            target = next((a for a in inbox if a.get("report")), None) or (inbox[0] if inbox else None)

        if not target:
            sid = "p2p_rub_offshore"
            report = (await self._demo.run(sid)).to_dict()
            meta = get_scenario_meta(sid)
            target = {
                "scenario_id": sid,
                "alert_code": "STR-DEMO-IC08",
                "case_ref": report["case_ref"],
                "instruments": meta.instruments,
                "typology_code": meta.typology_code,
                "legal_signs_ru": meta.legal_signs_ru,
                "subject_category_ru": meta.subject_category_ru,
            }
        else:
            report = target.get("report")
            if not report:
                report = (await self._demo.run(target["scenario_id"])).to_dict()

        if target.get("fz115_report"):
            fz115 = target["fz115_report"]
        else:
            fz115 = self._fz115.build(alert=target, investigation_report=report).to_dict()

        return {
            "summary_ru": f"Сформирована справка {fz115['report_id']}: {fz115['decision_ru'][:80]}…",
            "metrics": {"reports_month": NATIONAL_METRICS["reports_fz115_month"]},
            "output": {"fz115_report": fz115},
            "log_lines": [
                "Template: 115-ФЗ справка о проверке",
                f"Report ID: {fz115['report_id']}",
                f"Decision: {fz115['decision_ru'][:60]}…",
            ],
        }
