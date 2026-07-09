"""Periodic health-check for Scalpel collectors."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.osint_core.scalpel.registry import SCALPEL_COLLECTORS, registry_manifest

_CHECK_INTERVAL_MIN = int(os.getenv("FINSKALP_COLLECTOR_HEALTH_MIN", "15"))
_HEALTH_RUN_TIMEOUT_SEC = float(os.getenv("FINSKALP_COLLECTOR_HEALTH_TIMEOUT_SEC", "45"))
_PING_TIMEOUT_SEC = float(os.getenv("FINSKALP_COLLECTOR_PING_TIMEOUT_SEC", "6"))
_last_run: float = 0.0
_cache: dict[str, Any] = {}
_bg_health_task: asyncio.Task[None] | None = None


@dataclass
class CollectorHealth:
    collector_id: str
    status: str
    latency_ms: int | None = None
    detail: str = ""
    checked_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "collector_id": self.collector_id,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "detail": self.detail,
            "checked_at": self.checked_at,
        }


# Minimal test queries per collector (from TOOL_CHECKLIST pattern)
_TEST_QUERIES: dict[str, dict[str, str]] = {
    "onchain_explorer": {"address": "T9yD14Nj9j7xAR4oQL3FzRPiRYiH5b8q", "chain": "tron"},
    "sanctions_watchlist": {"address": "T9yD14Nj9j7xAR4oQL3FzRPiRYiH5b8q", "chain": "tron"},
    "abuse_scam_registry": {"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "chain": "btc"},
    "darknet_index": {"address": "test", "chain": "tron"},
    "username_social": {"address": "testuser", "chain": "tron"},
}


def get_collector_health_snapshot() -> dict[str, Any]:
    """Non-blocking snapshot for liveness/readiness probes — never pings collectors."""
    if _cache:
        out = dict(_cache)
        out["source"] = "cache"
        return out
    return {
        "status": "warming",
        "collectors_ok": 0,
        "collectors_total": len(SCALPEL_COLLECTORS),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "interval_minutes": _CHECK_INTERVAL_MIN,
        "collectors": [],
        "registry_count": len(SCALPEL_COLLECTORS),
        "source": "snapshot",
        "detail_ru": "Фоновая проверка коллекторов ещё не завершена",
    }


async def ping_collector(collector_cls: type, *, timeout: float | None = None) -> CollectorHealth:
    cid = getattr(collector_cls, "collector_id", collector_cls.__name__)
    now = datetime.now(timezone.utc).isoformat()
    from flowsint_crypto_compliance.osint_core.scalpel.network_gateway import NetworkGateway

    gw = NetworkGateway()
    collector = collector_cls(gw)
    q = _TEST_QUERIES.get(cid, {"address": "T9yD14Nj9j7xAR4oQL3FzRPiRYiH5b8q", "chain": "tron"})
    from flowsint_types.fiat_crypto import Chain

    chain = Chain.TRON
    try:
        chain = Chain(q.get("chain", "tron"))
    except Exception:
        pass
    ping_timeout = timeout if timeout is not None else _PING_TIMEOUT_SEC
    t0 = time.perf_counter()
    try:
        res = await asyncio.wait_for(
            collector.collect(q["address"], chain, context={"health_check": True}),
            timeout=ping_timeout,
        )
        ms = int((time.perf_counter() - t0) * 1000)
        st = res.to_status() if hasattr(res, "to_status") else "ok"
        status = "ok" if not str(st).startswith("error") else "degraded"
        return CollectorHealth(collector_id=cid, status=status, latency_ms=ms, detail=str(st), checked_at=now)
    except asyncio.TimeoutError:
        return CollectorHealth(
            collector_id=cid,
            status="timeout",
            latency_ms=int(ping_timeout * 1000),
            detail="health_check_timeout",
            checked_at=now,
        )
    except Exception as exc:
        return CollectorHealth(
            collector_id=cid,
            status="error",
            detail=exc.__class__.__name__,
            checked_at=now,
        )


async def _run_collector_health_check_impl(*, force: bool = False, quick: bool = False) -> dict[str, Any]:
    global _last_run, _cache
    now = time.time()
    if quick and not force and not _cache:
        return get_collector_health_snapshot()
    if not force and _cache and (now - _last_run) < _CHECK_INTERVAL_MIN * 60:
        out = dict(_cache)
        out["source"] = "cache"
        return out

    ping_ids = set(_TEST_QUERIES) | {"onchain_explorer", "sanctions_watchlist"}
    classes = [c for c in SCALPEL_COLLECTORS if getattr(c, "collector_id", "") in ping_ids]
    if not classes:
        classes = SCALPEL_COLLECTORS[:4]

    results = await asyncio.gather(*[ping_collector(c) for c in classes], return_exceptions=True)
    rows: list[dict[str, Any]] = []
    for r in results:
        if isinstance(r, CollectorHealth):
            rows.append(r.to_dict())
        else:
            rows.append({"status": "error", "detail": str(r)})

    ok = sum(1 for r in rows if r.get("status") == "ok")
    payload = {
        "status": "ok" if ok >= len(rows) // 2 else "degraded",
        "collectors_ok": ok,
        "collectors_total": len(rows),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "interval_minutes": _CHECK_INTERVAL_MIN,
        "collectors": rows,
        "registry": registry_manifest(),
        "source": "live",
    }
    _last_run = now
    _cache = payload
    return payload


async def run_collector_health_check(*, force: bool = False, quick: bool = False) -> dict[str, Any]:
    """Full collector ping — use /api/osint/collector-health, not /api/health."""
    try:
        return await asyncio.wait_for(
            _run_collector_health_check_impl(force=force, quick=quick),
            timeout=_HEALTH_RUN_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "collectors_ok": 0,
            "collectors_total": 0,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "interval_minutes": _CHECK_INTERVAL_MIN,
            "collectors": [],
            "detail_ru": "Проверка коллекторов превысила лимит времени",
            "source": "timeout",
        }


async def start_collector_health_daemon() -> None:
    """Background refresh so /api/health never blocks on outbound collector pings."""
    global _bg_health_task
    if _bg_health_task and not _bg_health_task.done():
        return

    async def _loop() -> None:
        await asyncio.sleep(3)
        while True:
            try:
                await run_collector_health_check(force=True, quick=False)
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            await asyncio.sleep(_CHECK_INTERVAL_MIN * 60)

    _bg_health_task = asyncio.create_task(_loop())


async def stop_collector_health_daemon() -> None:
    global _bg_health_task
    if _bg_health_task is None:
        return
    _bg_health_task.cancel()
    try:
        await _bg_health_task
    except asyncio.CancelledError:
        pass
    _bg_health_task = None
