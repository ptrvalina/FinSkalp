"""Реестр 7 live-коллекторов FinSkalp (battle mode)."""

from __future__ import annotations

from typing import Any, Callable, Awaitable

from flowsint_crypto_compliance.osint_core import live_collectors as lc

LiveFn = Callable[..., Awaitable[dict[str, Any]]]

LIVE_COLLECTOR_REGISTRY: dict[str, dict[str, Any]] = {
    "collect_tron_chain": {
        "fn": lc.collect_tron_chain,
        "param": "address",
        "name_ru": "TronGrid · TRX-транзакции",
        "chain": "tron",
        "celery_task": "live_collect_tron_chain",
    },
    "collect_tron_trc20_transfers": {
        "fn": lc.collect_tron_trc20_transfers,
        "param": "address",
        "name_ru": "TronGrid · USDT/TRC20",
        "chain": "tron",
        "celery_task": "live_collect_tron_trc20",
    },
    "collect_btc_chain": {
        "fn": lc.collect_btc_chain,
        "param": "address",
        "name_ru": "mempool.space · BTC",
        "chain": "btc",
        "celery_task": "live_collect_btc_chain",
    },
    "collect_bsc_chain": {
        "fn": lc.collect_bsc_chain,
        "param": "address",
        "name_ru": "BscScan · BNB/BEP20",
        "chain": "bsc",
        "celery_task": "live_collect_bsc_chain",
        "env": ["BSCSCAN_API_KEY"],
    },
    "collect_eth_chain": {
        "fn": lc.collect_eth_chain,
        "param": "address",
        "name_ru": "Etherscan · ETH/ERC20",
        "chain": "eth",
        "celery_task": "live_collect_eth_chain",
        "env": ["ETHERSCAN_API_KEY"],
    },
    "collect_polygon_chain": {
        "fn": lc.collect_polygon_chain,
        "param": "address",
        "name_ru": "Blockscout · Polygon/MATIC",
        "chain": "polygon",
        "celery_task": "live_collect_polygon_chain",
        "env": ["FINSKALP_BLOCKSCOUT_POLYGON_URL"],
    },
    "collect_solana_chain": {
        "fn": lc.collect_solana_chain,
        "param": "address",
        "name_ru": "Solana RPC · signatures",
        "chain": "solana",
        "celery_task": "live_collect_solana_chain",
        "env": ["FINSKALP_SOLANA_RPC_URL"],
    },
    "collect_sanctions": {
        "fn": lc.collect_sanctions,
        "param": "query",
        "name_ru": "OpenSanctions · live search",
        "celery_task": "live_collect_sanctions",
    },
    "collect_bitcoinabuse": {
        "fn": lc.collect_bitcoinabuse,
        "param": "address",
        "name_ru": "BitcoinAbuse · crowd reports",
        "chain": "btc",
        "celery_task": "live_collect_bitcoinabuse",
        "env": ["BITCOINABUSE_API_KEY"],
    },
    "collect_maigret": {
        "fn": lc.collect_maigret,
        "param": "username",
        "name_ru": "Maigret · 500+ соцсетей",
        "celery_task": "live_collect_maigret",
    },
    "collect_ahmia": {
        "fn": lc.collect_ahmia,
        "param": "query",
        "name_ru": "Ahmia.fi · .onion index",
        "celery_task": "live_collect_ahmia",
    },
}


async def run_live_collector(collector_id: str, value: str) -> dict[str, Any]:
    meta = LIVE_COLLECTOR_REGISTRY.get(collector_id)
    if not meta:
        raise KeyError(f"Unknown live collector: {collector_id}")
    fn: LiveFn = meta["fn"]
    return await fn(value)


def list_live_collectors() -> list[dict[str, Any]]:
    return [
        {
            "id": cid,
            "name_ru": m["name_ru"],
            "param": m["param"],
            "celery_task": m.get("celery_task"),
            "chain": m.get("chain"),
            "requires_env": m.get("env", []),
        }
        for cid, m in LIVE_COLLECTOR_REGISTRY.items()
    ]
