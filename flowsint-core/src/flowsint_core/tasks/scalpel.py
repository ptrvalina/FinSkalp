from __future__ import annotations

import asyncio
import base64
import os
from typing import Any

from celery import states

from flowsint_core.core.celery import celery
from flowsint_crypto_compliance.infrastructure.idempotency import IdempotencyStore, make_idempotency_key
from flowsint_crypto_compliance.observability.tracing import trace_celery_task


def _run_async(coro: Any) -> Any:
    return asyncio.run(coro)


def _collector_task_impl(
    collector_id: str,
    address: str,
    chain: str,
    *,
    counterparties: list[str] | None = None,
    usernames: list[str] | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.scalpel.network_gateway import (
        NetworkGateway,
        NetworkGatewayConfig,
    )
    from flowsint_crypto_compliance.osint_core.scalpel.registry import SCALPEL_COLLECTORS
    from flowsint_types.fiat_crypto import Chain

    timeout = float(os.getenv("FINSKALP_HTTP_TIMEOUT", "12"))
    cfg = NetworkGatewayConfig.from_env()
    cfg.timeout_sec = timeout
    gw = NetworkGateway(config=cfg)

    collector_cls = next(c for c in SCALPEL_COLLECTORS if c.collector_id == collector_id)
    collector = collector_cls(gw)
    context: dict[str, Any] = {"usernames": usernames or [], "mentions": []}
    result = _run_async(
        collector.collect(
            address,
            Chain(chain.lower()),
            counterparties=counterparties,
            context=context,
        )
    )
    return {
        "collector_id": collector_id,
        "status": result.to_status(),
        "hits": [h.to_dict() for h in result.hits],
        "entities": result.entities,
    }


def _register_collector_task(collector_id: str, task_name: str) -> Any:
    @celery.task(name=task_name, bind=True)
    @trace_celery_task(task_name)
    def _task(
        self,
        address: str,
        chain: str,
        *,
        counterparties: list[str] | None = None,
        usernames: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        self.update_state(state=states.STARTED, meta={"phase": task_name, "collector": collector_id})
        return _collector_task_impl(
            collector_id,
            address,
            chain,
            counterparties=counterparties,
            usernames=usernames,
        )

    return _task


scalpel_collect_onchain = _register_collector_task("onchain_explorer", "scalpel_collect_onchain")
scalpel_collect_sanctions = _register_collector_task("sanctions_watchlist", "scalpel_collect_sanctions")
scalpel_collect_username = _register_collector_task("username_social", "scalpel_collect_username")
scalpel_collect_abuse = _register_collector_task("abuse_scam_registry", "scalpel_collect_abuse")
scalpel_collect_darknet = _register_collector_task("darknet_index", "scalpel_collect_darknet")
scalpel_collect_vasp = _register_collector_task("vasp_registry", "scalpel_collect_vasp")
scalpel_collect_court = _register_collector_task("court_enforcement", "scalpel_collect_court")
scalpel_collect_dns = _register_collector_task("reverse_whois_dns", "scalpel_collect_dns")

SCALPEL_COLLECTOR_TASK_NAMES = [
    "scalpel_collect_onchain",
    "scalpel_collect_sanctions",
    "scalpel_collect_username",
    "scalpel_collect_abuse",
    "scalpel_collect_darknet",
    "scalpel_collect_vasp",
    "scalpel_collect_court",
    "scalpel_collect_dns",
]


@celery.task(name="run_scalpel_collect", bind=True)
@trace_celery_task("run_scalpel_collect")
def run_scalpel_collect(
    self,
    address: str,
    chain: str,
    *,
    depth: int = 1,
    counterparties: list[str] | None = None,
    usernames: list[str] | None = None,
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Полный FinSkalp Scalpel OSINT (8 легальных коллекторов параллельно)."""
    from flowsint_crypto_compliance.infrastructure.idempotency import IdempotencyStore, make_idempotency_key
    from flowsint_crypto_compliance.osint_core.scalpel import ScalpelEngine
    from flowsint_types.fiat_crypto import Chain

    idem = idempotency_key or make_idempotency_key("scalpel", chain, address, str(depth))
    store = IdempotencyStore()
    if store.acquire("run_scalpel_collect", idem) == "done":
        cached = store.get_result("run_scalpel_collect", idem)
        if cached is not None:
            return cached

    self.update_state(state=states.STARTED, meta={"phase": "scalpel_collect"})
    try:
        engine = ScalpelEngine(timeout=float(os.getenv("FINSKALP_HTTP_TIMEOUT", "12")))
        result = _run_async(
            engine.collect(
                address,
                Chain(chain.lower()),
                counterparties=counterparties,
                depth=depth,
                usernames=usernames,
            )
        )
        payload = result.to_dict()
        store.complete("run_scalpel_collect", idem, payload)
        return payload
    except Exception:
        store.release("run_scalpel_collect", idem)
        raise


@celery.task(name="run_maigret_scan", bind=True)
def run_maigret_scan(
    self,
    username: str,
    *,
    top_sites: int = 120,
    use_tor: bool = False,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.scalpel.workers.maigret_runner import run_maigret

    self.update_state(state=states.STARTED, meta={"phase": "maigret", "username": username})
    return run_maigret(username, top_sites=top_sites, use_tor=use_tor)


@celery.task(name="run_spiderfoot_scan", bind=True)
def run_spiderfoot_scan(
    self,
    target: str,
    *,
    modules: list[str] | None = None,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.osint_core.scalpel.workers.spiderfoot_runner import (
        run_spiderfoot,
    )

    self.update_state(state=states.STARTED, meta={"phase": "spiderfoot", "target": target})
    return run_spiderfoot(target, modules=modules)


@celery.task(name="run_ocr_extract", bind=True)
def run_ocr_extract(
    self,
    filename: str,
    data_b64: str,
    *,
    backend: str = "auto",
) -> dict[str, Any]:
    from flowsint_crypto_compliance.reporting.ocr_pipeline import OCRPipeline

    self.update_state(state=states.STARTED, meta={"phase": "ocr", "filename": filename})
    raw = base64.b64decode(data_b64)
    return OCRPipeline().process_bytes(raw, filename, backend=backend).to_dict()


@celery.task(name="ingest_enforcement_notices", bind=True)
def ingest_enforcement_notices(self) -> dict[str, Any]:
    """Scheduled ingest: DOJ + Europol public enforcement RSS."""
    from flowsint_crypto_compliance.ingestion.enforcement_feeds import ingest_enforcement_feeds

    self.update_state(state=states.STARTED, meta={"phase": "enforcement_ingest"})
    return ingest_enforcement_feeds()
