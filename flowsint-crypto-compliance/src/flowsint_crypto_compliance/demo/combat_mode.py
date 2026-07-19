"""Combat (production) mode — real on-chain / live fusion, no synthetic scenario runner."""

from __future__ import annotations

import os
from typing import Any

from flowsint_crypto_compliance.osint_core.multihop_fusion import is_live_address
from flowsint_crypto_compliance.services.wallet_screening import infer_chain
from flowsint_types.fiat_crypto import Chain


def is_regulator_stand() -> bool:
    """True when running flowsint-regulator-stand (:8877 demo surface)."""
    return os.getenv("FINSKALP_REGULATOR_STAND", "0").strip().lower() in ("1", "true", "yes")


def is_combat_mode() -> bool:
    """Default ON for regulator stand — set COMPLIANCE_COMBAT_MODE=0 only for offline dev."""
    return os.getenv("COMPLIANCE_COMBAT_MODE", "1").strip().lower() in ("1", "true", "yes")


def resolve_entity_store_mode() -> str:
    """Postgres in combat mode unless FINSKALP_ENTITY_STORE is explicitly set."""
    raw = os.getenv("FINSKALP_ENTITY_STORE", "").strip().lower()
    if raw:
        return raw
    # Demo stand (:8877) must not share production entity_labels unless explicitly opted in.
    if is_regulator_stand() and os.getenv("FINSKALP_DEMO_STAND_SHARE_PROD_DB", "0") != "1":
        return "memory"
    return "postgres" if is_combat_mode() else "memory"


def apply_combat_env_defaults() -> None:
    """Set combat-mode defaults without overriding explicit env."""
    if not os.getenv("FINSKALP_ENTITY_STORE", "").strip():
        if is_regulator_stand() and os.getenv("FINSKALP_DEMO_STAND_SHARE_PROD_DB", "0") != "1":
            os.environ["FINSKALP_ENTITY_STORE"] = "memory"
        elif is_combat_mode():
            os.environ["FINSKALP_ENTITY_STORE"] = "postgres"

    if not is_combat_mode():
        return

    # Production feature flags — only set when unset so operators can override
    combat_flags = {
        "FINSKALP_ECCF_POSTGRES_PERSISTENCE": "1",
        "FINSKALP_WORKSPACE_FULL_PANELS": "1",
        "FINSKALP_ENTERPRISE_REPORT_SECTIONS": "1",
        "FINSKALP_IDOO_REAL_HEALTH_PROBES": "1",
        "COMPLIANCE_DEMO_MODE": "0",
        "FINSKALP_MAIGRET_TOP_SITES": "40",
        "FINSKALP_MAIGRET_TIMEOUT": "45",
        "FINSKALP_MAIGRET_USERNAMES": "1",
        "FINSKALP_COLLECTOR_TIMEOUT_SEC": "55",
        "COMPLIANCE_INVESTIGATE_TIMEOUT_SEC": "900",
    }
    for key, value in combat_flags.items():
        if not os.getenv(key, "").strip():
            os.environ[key] = value


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
