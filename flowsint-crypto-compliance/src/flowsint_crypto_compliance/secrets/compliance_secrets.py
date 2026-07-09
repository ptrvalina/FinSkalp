"""Compliance secrets — env first, Vault fallback."""

from __future__ import annotations

import os


def get_compliance_secret(key: str, *, default: str | None = None) -> str | None:
    env_key = key.upper().replace(":", "_").replace("-", "_")
    if os.getenv(env_key):
        return os.getenv(env_key)
    mapped = {
        "webhook": "COMPLIANCE_WEBHOOK_SECRET",
        "trongrid": "TRONGRID_API_KEY",
        "bitcoinabuse": "BITCOINABUSE_API_KEY",
        "regulator_hub": "REGULATOR_HUB_TOKEN",
    }
    for suffix, env in mapped.items():
        if suffix in key.lower() and os.getenv(env):
            return os.getenv(env)
    try:
        from flowsint_core.core.services.vault_service import VaultService

        owner = os.getenv("COMPLIANCE_VAULT_OWNER_ID")
        if owner:
            vault = VaultService()
            val = vault.get_secret(owner, key)
            if val:
                return val
    except Exception:
        pass
    return default
