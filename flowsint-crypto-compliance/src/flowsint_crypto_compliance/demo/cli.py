"""CLI entry point for regulator demo."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys


def main() -> None:
    sys.exit(asyncio.run(_async_main()))


async def _async_main() -> int:
    parser = argparse.ArgumentParser(
        description="Flowsint Compliance — демо для госрегулятора (РФ)"
    )
    parser.add_argument(
        "--scenario",
        choices=["all", "p2p_rub_offshore", "cis_transit_kz", "cross_border_do", "sbp_gray_hub"],
        default="all",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    from flowsint_crypto_compliance.demo.runner import RegulatorDemoRunner

    runner = RegulatorDemoRunner()

    if args.list:
        for s in runner.list_scenarios():
            print(f"  {s['id']}: {s['title_ru']}")
        return 0

    reports = (
        await runner.run_all()
        if args.scenario == "all"
        else [await runner.run(args.scenario)]
    )

    if args.json:
        print(json.dumps([r.to_dict() for r in reports], ensure_ascii=False, indent=2))
        return 0

    for report in reports:
        _print_report(report)
    return 0


def _print_report(report) -> None:
    def out(text: str) -> None:
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))

    bar = "=" * 72
    out(bar)
    out(f"  КЕЙС: {report.case_ref}")
    out(f"  СЦЕНАРИЙ: {report.scenario_title_ru}")
    out(f"  РИСК: {report.risk_level.upper()} | ИНДЕКС: {report.illegal_flow_score}/100")
    out(bar)
    out(f"\n{report.executive_summary_ru}\n")
    out("--- МЕТРИКИ ---")
    for k, v in report.metrics.items():
        out(f"  {k}: {v}")
    out(f"\n--- ВЫЯВЛЕНИЯ ({len(report.findings)}) ---")
    for i, f in enumerate(report.findings, 1):
        out(f"\n  [{i}] [{f.severity.upper()}] {f.title_ru}")
        out(f"      {f.description_ru}")
        if f.addresses:
            out(f"      Адреса: {', '.join(f.addresses[:3])}")
    out(f"\n--- ГРАФ --- узлов: {report.evidence_graph['nodes']}, рёбер: {report.evidence_graph['edges']}")
    out("")


if __name__ == "__main__":
    main()
