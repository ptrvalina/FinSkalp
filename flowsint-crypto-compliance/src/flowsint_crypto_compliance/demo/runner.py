from __future__ import annotations

from flowsint_crypto_compliance.demo.chain_data import get_demo_adapters
from flowsint_crypto_compliance.demo.demo_context import get_demo_label_cache
from flowsint_crypto_compliance.demo.scenarios import SCENARIOS, DemoScenario, get_scenario, list_scenarios
from flowsint_crypto_compliance.ingestion.bank_regulator import bank_feed_to_fiat_event
from flowsint_crypto_compliance.osint_core.fusion_engine import InvestigationBundle, OSINTFusionEngine
from flowsint_crypto_compliance.osint_core.fusion_engine import FusionResult
from flowsint_crypto_compliance.reporting.regulator_report import RegulatorCaseReport, ReportBuilder


class RegulatorDemoRunner:
    """
    Боевой демо-прототип: полный цикл OSINT для показа госрегулятору.

    Работает автономно (без БД) — идеально для стенда и презентации.
    """

    def __init__(self) -> None:
        self._reporter = ReportBuilder()
        self._last_fusion: FusionResult | None = None

    @staticmethod
    def list_scenarios() -> list[dict[str, str]]:
        return list_scenarios()

    async def run(self, scenario_id: str) -> RegulatorCaseReport:
        scenario = get_scenario(scenario_id)
        return await self._run_scenario(scenario)

    async def run_all(self) -> list[RegulatorCaseReport]:
        reports = []
        for sid in SCENARIOS:
            reports.append(await self.run(sid))
        return reports

    async def _run_scenario(self, scenario: DemoScenario) -> RegulatorCaseReport:
        adapters = get_demo_adapters(scenario.id)
        engine = OSINTFusionEngine(
            chain_adapters=adapters,
            label_cache=get_demo_label_cache(),
        )

        for label in scenario.registry_labels:
            engine.label_cache.put(label)

        fiat = [bank_feed_to_fiat_event(b) for b in scenario.bank_feeds]
        bundle = InvestigationBundle(
            case_id=scenario.case_ref,
            bank_feeds=scenario.bank_feeds,
            fiat_events=fiat,
            licensed_events=scenario.licensed_events,
            control_purchases=scenario.control_purchases,
            registry_labels=scenario.registry_labels,
        )
        fusion = await engine.fuse(bundle)
        self._last_fusion = fusion
        return self._reporter.build(
            case_ref=scenario.case_ref,
            scenario_title_ru=scenario.title_ru,
            fusion=fusion,
            bank_feed_count=len(scenario.bank_feeds),
            control_purchase_count=len(scenario.control_purchases),
            registry_label_count=engine.label_cache.count(),
        )

    def graph_viz_for_last_run(self, report: RegulatorCaseReport) -> dict | None:
        if not self._last_fusion:
            return None
        from flowsint_crypto_compliance.demo.graph_viz_adapter import evidence_graph_to_viz

        return evidence_graph_to_viz(self._last_fusion.graph, report.findings)
