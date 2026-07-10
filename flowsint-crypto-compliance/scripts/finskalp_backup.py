#!/usr/bin/env python3
"""Run a local FinSkalp backup bundle (RFC-0021 / Wave 4)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "flowsint-types" / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description="FinSkalp local backup runner")
    parser.add_argument("--dry-run", action="store_true", help="Plan bundle without writing files")
    args = parser.parse_args()

    from flowsint_crypto_compliance.platform.v2.idoo.backup_runner import run_backup

    result = run_backup(dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
