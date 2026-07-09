"""Solana JSON-RPC helpers for live collectors."""

from __future__ import annotations

import os
from typing import Any

import httpx

_DEFAULT_RPC = "https://api.mainnet-beta.solana.com"
_RPC_ENV = "FINSKALP_SOLANA_RPC_URL"


def solana_rpc_url() -> str:
    return os.getenv(_RPC_ENV, _DEFAULT_RPC).strip() or _DEFAULT_RPC


async def solana_rpc(
    method: str,
    params: list[Any],
    *,
    timeout: float = 12.0,
) -> dict[str, Any]:
    """POST JSON-RPC to configured Solana endpoint (rate-limited on public RPC)."""
    url = solana_rpc_url()
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    headers = {"Content-Type": "application/json", "User-Agent": "FinSkalp-Live/1.0"}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise ValueError(body["error"].get("message") or str(body["error"]))
        return body.get("result") or {}


async def fetch_address_activity(address: str, *, limit: int = 25) -> dict[str, Any]:
    """Signatures + parsed transfer hints for a Solana base58 address."""
    sigs = await solana_rpc(
        "getSignaturesForAddress",
        [address, {"limit": min(limit, 40)}],
    )
    signatures = sigs if isinstance(sigs, list) else []
    transfers: list[dict[str, Any]] = []
    counterparties: list[str] = []
    for entry in signatures[:limit]:
        if not isinstance(entry, dict):
            continue
        sig = entry.get("signature") or ""
        block_time = entry.get("blockTime")
        ts_ms = int(block_time) * 1000 if block_time else None
        err = entry.get("err")
        if err:
            continue
        transfers.append(
            {
                "from": address,
                "to": "",
                "amount": None,
                "timestamp": ts_ms,
                "tx_hash": sig,
                "asset": "SOL",
                "direction": "activity",
            }
        )
    return {
        "status": 200,
        "source": "solana_rpc",
        "rpc_url": solana_rpc_url(),
        "chain": "solana",
        "address": address,
        "tx_count": len(signatures),
        "counterparties": counterparties,
        "transfers": transfers,
    }
