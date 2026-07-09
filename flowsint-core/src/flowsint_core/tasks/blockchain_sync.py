"""Celery tasks — RFC-0013 incremental blockchain sync."""

from __future__ import annotations

import os
from typing import Any

from celery import states

from flowsint_core.core.celery import celery


def _run(coro):
    import asyncio

    return asyncio.run(coro)


@celery.task(name="sync_blockchain_chains_incremental", bind=True)
def sync_blockchain_chains_incremental(self, chains: list[str] | None = None) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.block_sync import (
        sync_all_chains,
        sync_chain_incremental,
    )

    combat_mode = os.getenv("COMPLIANCE_COMBAT_MODE", "1").strip().lower() in ("1", "true", "yes")
    simulate = not combat_mode
    self.update_state(state=states.STARTED, meta={"task": "block_sync"})
    if chains:
        results = []
        for ch in chains:
            results.append(_run(sync_chain_incremental(ch, simulate=simulate)))
        return {"ok": True, "results": results}
    return _run(sync_all_chains(simulate=simulate))
