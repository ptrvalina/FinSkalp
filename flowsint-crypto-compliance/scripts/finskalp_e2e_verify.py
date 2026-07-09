#!/usr/bin/env python3
"""Full live E2E verification — TronGrid with API key, all 3 addresses, stage timings."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "flowsint-types" / "src"))
sys.path.insert(0, str(ROOT.parent / "flowsint-core" / "src"))

from flowsint_crypto_compliance.config.env_loader import load_project_env, trongrid_key_configured

DEMO = "TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL"
NEW = "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE"
CLEAN = "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"
TX_LIMIT = 300


async def _bootstrap_once() -> dict:
    from flowsint_crypto_compliance.attribution import AttributionEngine
    from flowsint_crypto_compliance.demo.demo_context import get_demo_label_cache

    os.environ.setdefault("FINSKALP_OFAC_REFRESH", "0")
    os.environ.setdefault("FINSKALP_OS_REFRESH", "0")
    engine = AttributionEngine(label_cache=get_demo_label_cache())
    return await engine.ensure_bootstrap()


async def _run_address(address: str, *, case: str) -> dict:
    from flowsint_crypto_compliance.demo.demo_context import get_demo_label_cache
    from flowsint_crypto_compliance.osint_core.multihop_fusion import MultiHopFusionEngine
    from flowsint_crypto_compliance.reporting.pdf_report import render_pdf_bytes
    from flowsint_crypto_compliance.services.wallet_screening import (
        WalletScreeningRequest,
        WalletScreeningService,
    )
    from flowsint_types.fiat_crypto import Chain

    timings: dict[str, int] = {}
    out: dict = {"case": case, "address": address}

    t0 = time.perf_counter()
    svc = WalletScreeningService(label_cache=get_demo_label_cache())
    result = await svc.screen(
        WalletScreeningRequest(address=address, chain=Chain.TRON, limit=TX_LIMIT)
    )
    screening = result.model_dump(mode="json")
    timings["screen_ms"] = int((time.perf_counter() - t0) * 1000)

    onchain = screening.get("onchain_summary") or {}
    attr = onchain.get("attribution") or {}
    timings["attribution_ms"] = timings["screen_ms"]

    t0 = time.perf_counter()
    try:
        mh = MultiHopFusionEngine(max_hops=1)
        graph = await mh.explore(address, "tron")
        fusion_dict = graph.to_dict()
        timings["fusion_graph_ms"] = int((time.perf_counter() - t0) * 1000)
        out["fusion_nodes"] = len(fusion_dict.get("nodes") or [])
    except Exception as exc:
        timings["fusion_graph_ms"] = int((time.perf_counter() - t0) * 1000)
        out["fusion_error"] = exc.__class__.__name__
        fusion_dict = {}

    t0 = time.perf_counter()
    try:
        from flowsint_crypto_compliance.attribution.attribution_engine import AttributionResult
        from flowsint_crypto_compliance.reporting.forensic_builder import (
            build_forensic_report_v2,
            resolve_priority_lead_live,
        )

        attr_result = AttributionResult(
            labels={},
            connections=attr.get("connections") or [],
            sanctions_hits=attr.get("sanctions_hits") or [],
            source_status=attr.get("source_status") or {},
            tier_summary=attr.get("tier_summary") or {},
        )
        outbound_n = onchain.get("outbound_count", 0)
        gross_out = float(onchain.get("outbound_amount") or 0)
        priority_lead = await resolve_priority_lead_live(
            subject_address=address,
            chain="tron",
            onchain=onchain,
            outbound_n=outbound_n,
            gross_out=gross_out,
        )
        forensic = build_forensic_report_v2(
            investigation_id=f"E2E-{case}",
            case_ref=f"E2E-{case.upper()}",
            address=address,
            chain="tron",
            screening=screening,
            attribution=attr_result,
            fusion_report={},
            fusion_graph=fusion_dict,
            graph_section=None,
            evidence_sources={"onchain": onchain},
            priority_lead=priority_lead,
        )
        html = f"<html><body><h1>{case}</h1><pre>{json.dumps(forensic.get('priority_tracing_lead'))}</pre></body></html>"
        pdf_bytes, media = render_pdf_bytes(html)
        timings["pdf_ms"] = int((time.perf_counter() - t0) * 1000)
        out["pdf_bytes"] = len(pdf_bytes)
        out["pdf_media"] = media
        out["priority_lead"] = forensic.get("priority_tracing_lead")
    except Exception as exc:
        timings["pdf_ms"] = int((time.perf_counter() - t0) * 1000)
        out["pdf_error"] = str(exc) or exc.__class__.__name__

    exp = onchain.get("kyt_exposure") or attr.get("exposure") or {}
    out.update(
        {
            "risk_score": screening.get("risk_score"),
            "connections": len(attr.get("connections") or exp.get("indirect_exposure") or []),
            "inbound": onchain.get("inbound_count"),
            "outbound": onchain.get("outbound_count"),
            "sanctions": attr.get("sanctions_hits", []),
            "timings_ms": timings,
            "total_ms": sum(timings.values()),
        }
    )
    return out


async def main() -> int:
    load_project_env()
    os.environ.setdefault("COMPLIANCE_COMBAT_MODE", "1")
    os.environ["FINSKALP_KYT_SAMPLES"] = "0"
    os.environ.setdefault("FINSKALP_MAX_HOPS", "1")
    os.environ.setdefault("FINSKALP_FUSION_MAX_COUNTERPARTIES", "6")
    os.environ.setdefault("FINSKALP_FUSION_TX_LIMIT", "50")

    if not trongrid_key_configured():
        print(
            json.dumps(
                {"pass": False, "error": "TRONGRID_API_KEY not loaded from .env"},
                indent=2,
            )
        )
        return 1

    from flowsint_crypto_compliance.reporting.evidence_inventory import (
        build_evidence_inventory,
        verify_exhibit_hash,
    )

    payload = {"test": True, "n": 1}
    inv = build_evidence_inventory(case_ref="E2E", sources={"probe": payload})
    hash_ok = verify_exhibit_hash(payload, inv[0]["sha256"])

    try:
        bootstrap_stats = await _bootstrap_once()
    except Exception as exc:
        print(
            json.dumps(
                {"pass": False, "error": f"bootstrap: {exc}", "hash_reproducible": hash_ok},
                indent=2,
            )
        )
        return 1

    results: list[dict] = []
    for case, addr in [("demo", DEMO), ("new_labeled", NEW), ("clean", CLEAN)]:
        print(f"E2E running: {case} …", flush=True)
        try:
            results.append(await _run_address(addr, case=case))
        except Exception as exc:
            results.append(
                {
                    "case": case,
                    "address": addr,
                    "error": str(exc) or exc.__class__.__name__,
                }
            )

    ok_cases = [
        r
        for r in results
        if not r.get("error")
        and not r.get("fusion_error")
        and not r.get("pdf_error")
        and r.get("inbound") is not None
    ]
    passed = hash_ok and len(ok_cases) == 3

    report = {
        "hash_reproducible": hash_ok,
        "trongrid_key_loaded": True,
        "bootstrap": bootstrap_stats,
        "cases": results,
        "pass": passed,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
