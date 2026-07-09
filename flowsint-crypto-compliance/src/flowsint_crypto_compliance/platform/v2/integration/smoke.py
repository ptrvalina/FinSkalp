"""End-to-end smoke pipeline for Platform v2 live checks."""

from __future__ import annotations

import os
import uuid
from typing import Any

from flowsint_crypto_compliance.demo.combat_mode import is_combat_mode
from flowsint_crypto_compliance.platform.v2.gateway import (
    analyze_blockchain_address,
    register_eccf_evidence,
    run_crif_check,
    run_icf_collect,
    run_rde_assess,
)
from flowsint_crypto_compliance.platform.v2.rde.signal_bridge import acquire_platform_signals


def _tenant_id() -> uuid.UUID:
    return uuid.UUID(os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001"))


def _result_ok(result: dict[str, Any]) -> bool:
    if "ok" in result:
        return bool(result["ok"])
    return "error" not in result


def _icf_connector() -> str:
    return os.getenv("FINSKALP_ICF_SMOKE_CONNECTOR", "osint.onchain").strip() or "osint.onchain"


async def run_live_smoke(case_ref: str, address: str, chain: str) -> dict[str, Any]:
    """Run a compact live-or-memory integration smoke through core platform modules."""
    tenant_id = _tenant_id()
    chain_key = chain.strip().lower()
    combat = is_combat_mode()
    steps: list[dict[str, Any]] = []

    try:
        blockchain = await analyze_blockchain_address(
            address=address.strip(),
            chain=chain_key,
            case_ref=case_ref,
            tenant_id=tenant_id,
            publish=True,
        )
        steps.append(
            {
                "step": "blockchain",
                "ok": _result_ok(blockchain),
                "mode": "real" if combat else "memory",
                "result": blockchain,
            }
        )

        icf_connector = _icf_connector()
        icf = await run_icf_collect(
            connector_id=icf_connector,
            tenant_id=tenant_id,
            query={
                "address": address.strip(),
                "chain": chain_key,
                "entity_type": "crypto_address",
                "entity_value": address.strip(),
            },
            case_ref=case_ref,
            publish=True,
        )
        steps.append(
            {
                "step": "icf",
                "ok": _result_ok(icf),
                "mode": "stub",
                "connector_id": icf_connector,
                "note": "Current ICF smoke uses registry/static connector contract.",
                "result": icf,
            }
        )

        crif = await run_crif_check(
            connector_id="registry.ofac",
            tenant_id=tenant_id,
            query={
                "entity_value": case_ref,
                "organization": case_ref,
                "name": case_ref,
            },
            case_ref=case_ref,
            organization_key=case_ref,
            publish=True,
        )
        steps.append(
            {
                "step": "crif",
                "ok": _result_ok(crif),
                "mode": "stub",
                "connector_id": "registry.ofac",
                "note": "Current CRIF smoke uses built-in registry connector simulation.",
                "result": crif,
            }
        )

        signals = await acquire_platform_signals(
            tenant_id=tenant_id,
            entity_key=address.strip(),
            case_ref=case_ref,
            input_signals={
                "blockchain_signals": {
                    "address": address.strip(),
                    "chain": chain_key,
                }
            },
        )
        steps.append(
            {
                "step": "signal_bridge",
                "ok": True,
                "mode": "auto",
                "result": {
                    "groups": list(signals.keys()),
                    "auto_acquired": (signals.get("_signal_bridge") or {}).get("auto_acquired", []),
                },
            }
        )

        rde = await run_rde_assess(
            entity_key=address.strip(),
            tenant_id=tenant_id,
            case_ref=case_ref,
            signals=signals,
        )
        steps.append(
            {
                "step": "rde",
                "ok": _result_ok(rde),
                "mode": "real" if combat else "memory",
                "result": rde,
            }
        )

        eccf = await register_eccf_evidence(
            tenant_id=tenant_id,
            case_ref=case_ref,
            collector_id="integration.smoke",
            source_uri=f"finskalp://integration-smoke/{case_ref}",
            bridge_kg=True,
            collector_payload={
                "entity_type": "crypto_address",
                "entity_value": address.strip(),
                "source_type": "integration.smoke",
                "payload": {
                    "chain": chain_key,
                    "case_ref": case_ref,
                    "blockchain": blockchain,
                    "icf": icf,
                    "crif": crif,
                    "rde": rde,
                },
            },
        )
        steps.append(
            {
                "step": "eccf",
                "ok": _result_ok(eccf),
                "mode": "memory",
                "result": eccf,
            }
        )
    except Exception as exc:
        steps.append({"step": "error", "ok": False, "error": str(exc)})

    return {
        "ok": all(step.get("ok") for step in steps),
        "case_ref": case_ref,
        "address": address.strip(),
        "chain": chain_key,
        "combat_mode": combat,
        "steps": steps,
    }
