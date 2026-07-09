"""Platform v2 bootstrap wiring for live/demo entrypoints."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from flowsint_crypto_compliance.demo.combat_mode import apply_combat_env_defaults, is_combat_mode

from .status import get_integration_status

_bootstrap_lock = asyncio.Lock()
_bootstrap_runs = 0
_sync_task: asyncio.Task[dict[str, Any]] | None = None


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _sync_done(task: asyncio.Task[dict[str, Any]]) -> None:
    global _sync_task
    _sync_task = None
    try:
        task.result()
    except Exception:
        pass


async def _maybe_trigger_initial_sync() -> dict[str, Any]:
    global _sync_task
    if not _bool_env("FINSKALP_PLATFORM_V2_BOOTSTRAP_SYNC", default=False):
        return {"scheduled": False, "reason": "disabled"}
    if _sync_task is not None and not _sync_task.done():
        return {"scheduled": False, "reason": "already_running"}

    from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.block_sync import sync_all_chains

    simulate = False if is_combat_mode() else None
    _sync_task = asyncio.create_task(sync_all_chains(simulate=simulate))
    _sync_task.add_done_callback(_sync_done)
    return {
        "scheduled": True,
        "simulate": simulate,
        "reason": "combat_live" if simulate is False else "default_mode",
    }


async def bootstrap_platform_v2() -> dict[str, Any]:
    """Apply runtime defaults and initialize shared platform v2 singletons."""
    global _bootstrap_runs

    async with _bootstrap_lock:
        apply_combat_env_defaults()

        from flowsint_crypto_compliance.platform.v2.crif.registry_catalog import (
            register_crif_registry_connectors,
        )
        from flowsint_crypto_compliance.platform.v2.event_bus import get_platform_event_bus
        from flowsint_crypto_compliance.platform.v2.event_subscriber import (
            get_platform_event_subscriber,
        )

        register_crif_registry_connectors()
        get_platform_event_subscriber()
        get_platform_event_bus()

        sync = await _maybe_trigger_initial_sync()
        _bootstrap_runs += 1

        return {
            "ok": True,
            "bootstrap_runs": _bootstrap_runs,
            "combat_mode": is_combat_mode(),
            "sync": sync,
            "status": get_integration_status(),
        }
