#!/usr/bin/env python3
"""CLI health check for FinSkalp sovereign TRON FullNode."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys


async def _main(url: str | None, *, json_out: bool) -> int:
    from flowsint_crypto_compliance.chains.on_chain_provider import tron_infra_status

    status = await tron_infra_status()
    if url:
        from flowsint_crypto_compliance.chains.on_chain_provider import probe_sovereign_node

        reachable, height = await probe_sovereign_node(url)
        status["sovereign_url"] = url
        status["sovereign_reachable"] = reachable
        status["sovereign_block_height"] = height

    if json_out:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        ok = "OK" if status.get("sovereign_reachable") else "DOWN"
        print(f"Sovereign TRON node [{status.get('sovereign_url')}]: {ok}")
        if status.get("sovereign_block_height") is not None:
            print(f"  Block height: {status['sovereign_block_height']}")
        print(f"  Provider mode: {status.get('provider_mode')}")
        print(f"  Active: {status.get('active_provider_label_ru')}")
        if status.get("snapshot_sync_state"):
            gate = "PASS" if status.get("snapshot_gate_passed") else "WAIT"
            print(f"  Snapshot sync: {status['snapshot_sync_state']} (gate {gate}, min height {status.get('snapshot_min_height')})")

    if status.get("snapshot_gate_passed") is False and status.get("sovereign_reachable"):
        return 2
    return 0 if status.get("sovereign_reachable") else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="FinSkalp TRON FullNode health check")
    parser.add_argument("--url", help="Override FINSKALP_TRON_SOVEREIGN_URL")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    try:
        from flowsint_crypto_compliance.config.env_loader import load_project_env

        load_project_env()
    except Exception:
        pass
    code = asyncio.run(_main(args.url, json_out=args.json))
    sys.exit(code)


if __name__ == "__main__":
    main()
