#!/usr/bin/env python3
"""CLI: запуск демо-прототипа для госрегулятора."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Flowsint Compliance — демо для госрегулятора (РФ)"
    )
    parser.add_argument(
        "--scenario",
        choices=["all", "p2p_rub_offshore", "cis_transit_kz", "cross_border_do", "sbp_gray_hub"],
        default="all",
        help="Сценарий для прогона",
    )
    parser.add_argument("--json", action="store_true", help="Вывод в JSON")
    parser.add_argument("--list", action="store_true", help="Список сценариев")
    args = parser.parse_args()

    from flowsint_crypto_compliance.demo.runner import RegulatorDemoRunner

    runner = RegulatorDemoRunner()

    if args.list:
        for s in runner.list_scenarios():
            print(f"  {s['id']}: {s['title_ru']}")
        return 0

    if args.scenario == "all":
        reports = await runner.run_all()
    else:
        reports = [await runner.run(args.scenario)]

    if args.json:
        print(json.dumps([r.to_dict() for r in reports], ensure_ascii=False, indent=2))
        return 0

    for report in reports:
        _print_report(report)
    return 0


def _print_report(report) -> None:
    bar = "=" * 72
    print(bar)
    print(f"  КЕЙС: {report.case_ref}")
    print(f"  СЦЕНАРИЙ: {report.scenario_title_ru}")
    print(f"  РИСК: {report.risk_level.upper()} | ИНДЕКС: {report.illegal_flow_score}/100")
    print(bar)
    print(f"\n{report.executive_summary_ru}\n")
    print("--- МЕТРИКИ ---")
    for k, v in report.metrics.items():
        print(f"  {k}: {v}")
    print(f"\n--- ВЫЯВЛЕНИЯ ({len(report.findings)}) ---")
    for i, f in enumerate(report.findings, 1):
        print(f"\n  [{i}] [{f.severity.upper()}] {f.title_ru}")
        print(f"      {f.description_ru}")
        if f.addresses:
            print(f"      Адреса: {', '.join(f.addresses[:3])}")
    print(f"\n--- ГРАФ ДОКАЗАТЕЛЬСТВ ---")
    print(f"  Узлов: {report.evidence_graph['nodes']}, рёбер: {report.evidence_graph['edges']}")
    print()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
