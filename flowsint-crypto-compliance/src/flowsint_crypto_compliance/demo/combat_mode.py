"""Combat (production) mode — real on-chain / live fusion, no synthetic scenario runner."""

from __future__ import annotations

import os
from typing import Any

from flowsint_crypto_compliance.osint_core.multihop_fusion import is_live_address
from flowsint_crypto_compliance.services.wallet_screening import infer_chain
from flowsint_types.fiat_crypto import Chain


def is_combat_mode() -> bool:
    """Default ON for regulator stand — set COMPLIANCE_COMBAT_MODE=0 only for offline dev."""
    return os.getenv("COMPLIANCE_COMBAT_MODE", "1").strip().lower() in ("1", "true", "yes")


def resolve_entity_store_mode() -> str:
    """Postgres in combat mode unless FINSKALP_ENTITY_STORE is explicitly set."""
    raw = os.getenv("FINSKALP_ENTITY_STORE", "").strip().lower()
    if raw:
        return raw
    return "postgres" if is_combat_mode() else "memory"


def apply_combat_env_defaults() -> None:
    """Set combat-mode defaults (entity store) without overriding explicit env."""
    if is_combat_mode() and not os.getenv("FINSKALP_ENTITY_STORE", "").strip():
        os.environ["FINSKALP_ENTITY_STORE"] = "postgres"


def combat_seed_address() -> tuple[str, Chain] | None:
    raw = os.getenv("FINSKALP_COMBAT_SEED_ADDRESS", "").strip()
    if not raw:
        return None
    chain_raw = os.getenv("FINSKALP_COMBAT_SEED_CHAIN", "").strip().lower()
    chain = Chain(chain_raw) if chain_raw else infer_chain(raw)
    return raw, chain


def resolve_crypto_from_scenario(scenario_id: str) -> tuple[str | None, Chain | None]:
    from flowsint_crypto_compliance.demo.scenarios import get_scenario

    scenario = get_scenario(scenario_id)
    for feed in scenario.bank_feeds:
        if feed.linked_crypto_address:
            chain = feed.linked_chain or infer_chain(feed.linked_crypto_address)
            return feed.linked_crypto_address, chain
    for cp in scenario.control_purchases:
        if cp.target_address:
            return cp.target_address, cp.chain
    for ev in scenario.licensed_events:
        if ev.address:
            return ev.address, ev.chain
    return None, None


def resolve_alert_crypto(alert: dict[str, Any]) -> tuple[str, Chain]:
    """Address for live investigation — alert fields, then env seed, never fake demo IDs in combat."""
    explicit = (alert.get("crypto_address") or "").strip()
    if explicit:
        chain_raw = alert.get("crypto_chain")
        chain = Chain(str(chain_raw).lower()) if chain_raw else infer_chain(explicit)
        return explicit, chain

    seed = combat_seed_address()
    if seed:
        return seed

    scenario_id = alert.get("scenario_id")
    if scenario_id:
        addr, chain = resolve_crypto_from_scenario(scenario_id)
        if addr and chain and is_live_address(addr, chain.value):
            return addr, chain

    raise ValueError(
        "Нет live-криптоадреса для расследования. "
        "Укажите crypto_address в СОО или задайте FINSKALP_COMBAT_SEED_ADDRESS в .env "
        "(реальный TRON/ETH/BTC адрес, не TRU_* demo)."
    )
