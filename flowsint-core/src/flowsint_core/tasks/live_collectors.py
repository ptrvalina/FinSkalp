"""Celery tasks for live collectors (battle mode)."""

from __future__ import annotations

from typing import Any

from celery import states
from celery.exceptions import Retry

from flowsint_core.core.celery import celery

_RETRY_KW = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 60,
    "retry_jitter": True,
    "max_retries": 3,
}


def _run(coro):
    import asyncio

    return asyncio.run(coro)


@celery.task(name="live_collect_tron_chain", bind=True, **_RETRY_KW)
def live_collect_tron_chain(self, address: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.live_collectors import collect_tron_chain

    self.update_state(state=states.STARTED, meta={"collector": "tron_chain"})
    return _run(collect_tron_chain(address))


@celery.task(name="live_collect_tron_trc20", bind=True, **_RETRY_KW)
def live_collect_tron_trc20(self, address: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.live_collectors import collect_tron_trc20_transfers

    self.update_state(state=states.STARTED, meta={"collector": "tron_trc20"})
    return _run(collect_tron_trc20_transfers(address))


@celery.task(name="live_collect_btc_chain", bind=True, **_RETRY_KW)
def live_collect_btc_chain(self, address: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.live_collectors import collect_btc_chain

    self.update_state(state=states.STARTED, meta={"collector": "btc_chain"})
    return _run(collect_btc_chain(address))


@celery.task(name="live_collect_bsc_chain", bind=True, **_RETRY_KW)
def live_collect_bsc_chain(self, address: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.live_collectors import collect_bsc_chain

    self.update_state(state=states.STARTED, meta={"collector": "bsc_chain"})
    return _run(collect_bsc_chain(address))


@celery.task(name="live_collect_eth_chain", bind=True, **_RETRY_KW)
def live_collect_eth_chain(self, address: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.live_collectors import collect_eth_chain

    self.update_state(state=states.STARTED, meta={"collector": "eth_chain"})
    return _run(collect_eth_chain(address))


@celery.task(name="live_collect_polygon_chain", bind=True, **_RETRY_KW)
def live_collect_polygon_chain(self, address: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.live_collectors import collect_polygon_chain

    self.update_state(state=states.STARTED, meta={"collector": "polygon_chain"})
    return _run(collect_polygon_chain(address))


@celery.task(name="live_collect_sanctions", bind=True, **_RETRY_KW)
def live_collect_sanctions(self, query: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.live_collectors import collect_sanctions

    self.update_state(state=states.STARTED, meta={"collector": "sanctions"})
    return _run(collect_sanctions(query))


@celery.task(name="live_collect_bitcoinabuse", bind=True, **_RETRY_KW)
def live_collect_bitcoinabuse(self, address: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.live_collectors import collect_bitcoinabuse

    self.update_state(state=states.STARTED, meta={"collector": "bitcoinabuse"})
    return _run(collect_bitcoinabuse(address))


@celery.task(name="live_collect_maigret", bind=True, **_RETRY_KW)
def live_collect_maigret(self, username: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.live_collectors import collect_maigret

    self.update_state(state=states.STARTED, meta={"collector": "maigret"})
    return _run(collect_maigret(username))


@celery.task(name="live_collect_ahmia", bind=True, **_RETRY_KW)
def live_collect_ahmia(self, query: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.live_collectors import collect_ahmia

    self.update_state(state=states.STARTED, meta={"collector": "ahmia"})
    return _run(collect_ahmia(query))


@celery.task(name="run_multihop_fusion", bind=True, **_RETRY_KW)
def run_multihop_fusion(
    self,
    address: str,
    chain: str,
    *,
    case_ref: str | None = None,
    max_hops: int = 3,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Multi-hop fusion + Neo4j persist + ML score."""
    from flowsint_crypto_compliance.infrastructure.idempotency import IdempotencyStore, make_idempotency_key
    from flowsint_crypto_compliance.ml.scoring_pipeline import score_fusion_graph
    from flowsint_crypto_compliance.osint_core.multihop_fusion import MultiHopFusionEngine
    from flowsint_crypto_compliance.storage.wallet_neo4j import WalletNeo4jStore

    idem = idempotency_key or make_idempotency_key("multihop", chain, address, str(max_hops))
    store = IdempotencyStore()
    state = store.acquire("run_multihop_fusion", idem)
    if state == "done":
        cached = store.get_result("run_multihop_fusion", idem)
        if cached is not None:
            return cached

    self.update_state(state=states.STARTED, meta={"phase": "multihop_fusion"})
    try:
        engine = MultiHopFusionEngine(max_hops=max_hops)
        graph = _run(engine.explore(address, chain.lower()))
        payload = graph.to_dict()
        ref = case_ref or f"LIVE-{chain.upper()}-{address[:12]}"
        payload["neo4j"] = WalletNeo4jStore().persist_fusion_graph(payload, case_ref=ref)
        payload["ml_score"] = score_fusion_graph(payload, address=address, chain=chain.lower())
        payload["case_ref"] = ref
        store.complete("run_multihop_fusion", idem, payload)
        return payload
    except Exception:
        store.release("run_multihop_fusion", idem)
        raise


LIVE_COLLECTOR_TASKS = [
    "live_collect_tron_chain",
    "live_collect_tron_trc20",
    "live_collect_btc_chain",
    "live_collect_bsc_chain",
    "live_collect_eth_chain",
    "live_collect_polygon_chain",
    "live_collect_sanctions",
    "live_collect_bitcoinabuse",
    "live_collect_maigret",
    "live_collect_ahmia",
    "run_multihop_fusion",
]
