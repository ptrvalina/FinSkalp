#!/usr/bin/env python3
"""Run attribution evaluation report (Evidently + precision/recall gate)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowsint_crypto_compliance.ml.attribution_eval import run_attribution_evaluation


async def main() -> int:
    result = await run_attribution_evaluation(engine_version="1.0")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    gate = (result.get("deploy_gate") or {})
    if gate.get("passed") is False:
        return 2
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
