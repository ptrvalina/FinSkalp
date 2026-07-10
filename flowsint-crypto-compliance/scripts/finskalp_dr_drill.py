#!/usr/bin/env python3
"""DR restore drill checklist (RFC-0021 / Wave 5)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    from flowsint_crypto_compliance.platform.v2.maturity.dr_runbook import dr_restore_runbook

    runbook = dr_restore_runbook()
    print(json.dumps(runbook, ensure_ascii=False, indent=2))
    return 0 if runbook.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
