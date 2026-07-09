#!/usr/bin/env python3
"""FinSkalp tool health checklist (Task 6)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "flowsint-types" / "src"))


async def main() -> int:
    rows: list[dict] = []

    async def check(name: str, coro):
        try:
            result = await coro
            rows.append({"tool": name, "status": "works", "detail": str(result)[:120]})
        except Exception as exc:
            rows.append({"tool": name, "status": "broken", "detail": str(exc)[:200]})

    from flowsint_crypto_compliance.osint_core.live_collectors import (
        collect_sanctions,
        collect_tron_trc20_transfers,
    )
    from flowsint_crypto_compliance.chains.tron import TronChainAdapter
    from flowsint_crypto_compliance.attribution import AttributionEngine
    from flowsint_crypto_compliance.reporting.evidence_inventory import build_evidence_inventory

    await check(
        "TronGrid TRC20",
        collect_tron_trc20_transfers("TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE", max_transfers=10),
    )
    await check("TronGrid balance", TronChainAdapter().get_account_state("TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE"))
    await check("OpenSanctions", collect_sanctions("TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL"))
    await check("Attribution bootstrap", AttributionEngine().ensure_bootstrap())
    await check(
        "Evidence hashes",
        asyncio.to_thread(
            lambda: build_evidence_inventory(case_ref="CHK", sources={"x": {"ok": True}})
        ),
    )

    print(json.dumps(rows, ensure_ascii=False, indent=2))
    broken = sum(1 for r in rows if r["status"] != "works")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
