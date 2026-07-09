"""
Пошаговое расследование: имитация боевого контура OSINT fusion.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Literal

from flowsint_crypto_compliance.demo.runner import RegulatorDemoRunner
from flowsint_crypto_compliance.demo.scenarios import DemoScenario, get_scenario

StepStatus = Literal["pending", "running", "done", "error"]


@dataclass(frozen=True)
class InvestigationStep:
    id: str
    label_ru: str
    detail_ru: str

    def to_dict(self, status: StepStatus = "pending", extra: str | None = None) -> dict[str, Any]:
        return {
            "id": self.id,
            "label_ru": self.label_ru,
            "detail_ru": extra or self.detail_ru,
            "status": status,
        }


PIPELINE_STEPS: list[InvestigationStep] = [
    InvestigationStep(
        "hub_ingest",
        "ИЦ-01 · Приём из хаба регулятора (115-ФЗ)",
        "Валидация сообщения банка по схеме regulator_hub_v1",
    ),
    InvestigationStep(
        "chain_fetch",
        "ИЦ-03 · On-chain разведка (BTC / ETH / TRON)",
        "Загрузка транзакций из публичных нод и построение графа",
    ),
    InvestigationStep(
        "registry_match",
        "ИЦ-05 · Сверка с суверенным реестром риск-меток",
        "Сопоставление адресов с перечнем 115-ФЗ и внутренними списками РФ/СНГ",
    ),
    InvestigationStep(
        "sovereign",
        "ИЦ-04 · Суверенная атрибуция (РФ/СНГ)",
        "Кластеризация, коридоры, чёрная/серая зона",
    ),
    InvestigationStep(
        "link_scoring",
        "ИЦ-03 · Склейка фиат ↔ крипто",
        "Linkage score, граф доказательств, мосты между регионами",
    ),
    InvestigationStep(
        "detection",
        "ИЦ-07 · Детектор нелегальных потоков",
        "Индикаторы обхода, mixer, трансгран, OTC hub (115-ФЗ ст. 6)",
    ),
    InvestigationStep(
        "report",
        "ИЦ-08 · Формирование отчётности ПОД/ФТ",
        "Справка по 115-ФЗ, решение, рекомендуемые действия",
    ),
]


class InvestigationPipeline:
    def __init__(self, *, step_delay_ms: int = 450) -> None:
        self._runner = RegulatorDemoRunner()
        self._step_delay_ms = step_delay_ms

    async def run(
        self,
        scenario_id: str,
        *,
        on_step: Any | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        scenario = get_scenario(scenario_id)
        steps_out: list[dict[str, Any]] = []

        for step in PIPELINE_STEPS:
            running = step.to_dict("running")
            steps_out.append(running)
            if on_step:
                await on_step(list(steps_out))

            detail = await self._step_detail(step.id, scenario)
            await asyncio.sleep(self._step_delay_ms / 1000)
            steps_out[-1] = step.to_dict("done", detail)
            if on_step:
                await on_step(list(steps_out))

        report = await self._runner.run(scenario_id)
        report_dict = report.to_dict()
        graph_viz = self._runner.graph_viz_for_last_run(report)
        if graph_viz:
            report_dict["graph_viz"] = graph_viz
        return steps_out, report_dict

    async def _step_detail(self, step_id: str, scenario: DemoScenario) -> str:
        feed = scenario.bank_feeds[0] if scenario.bank_feeds else None
        if step_id == "hub_ingest" and feed:
            return (
                f"STR принят: {feed.bank_name}, {feed.amount:,.0f} {feed.currency or 'RUB'}, "
                f"feed_id={feed.feed_id}"
            )
        if step_id == "chain_fetch":
            n_wallets = len({cp.target_address for cp in scenario.control_purchases} | {
                cp.source_address for cp in scenario.control_purchases if cp.source_address
            })
            n_wallets = max(n_wallets, 3)
            return f"Проанализировано {n_wallets}+ адресов на TRON/BTC/ETH"
        if step_id == "registry_match":
            n = len(scenario.registry_labels)
            if n:
                names = ", ".join(l.entity_name or l.category for l in scenario.registry_labels[:3])
                sanctioned = sum(1 for l in scenario.registry_labels if l.sanctioned)
                tail = f"; в перечне 115-ФЗ: {sanctioned}" if sanctioned else ""
                return f"Совпадений с суверенным реестром: {n} ({names}){tail}"
            return "Совпадений в реестре нет — суверенная on-chain атрибуция"
        if step_id == "sovereign":
            return "Коридоры RU/CIS, эвристики hub/mixer, black zone scoring"
        if step_id == "link_scoring" and feed and feed.linked_crypto_address:
            return f"Прямая склейка банк→{feed.linked_crypto_address[:12]}…"
        if step_id == "link_scoring":
            return "Связи банк↔крипто через контрольные закупки и VASP"
        if step_id == "detection":
            return "Проверка индикаторов 115-ФЗ / ПОД/ФТ / трансгран"
        if step_id == "report":
            return f"Кейс {scenario.case_ref} готов к передаче аналитику"
        return PIPELINE_STEPS[[s.id for s in PIPELINE_STEPS].index(step_id)].detail_ru
