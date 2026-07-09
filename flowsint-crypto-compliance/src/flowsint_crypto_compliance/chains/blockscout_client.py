"""Blockscout Etherscan-compatible API abstraction for EVM chains (ETH/BSC/Polygon)."""

from __future__ import annotations

import os
from typing import Any, Callable, Awaitable
from urllib.parse import quote

_CHAIN_CONFIG: dict[str, tuple[str, str]] = {
    "eth": ("FINSKALP_BLOCKSCOUT_ETH_URL", "https://eth.blockscout.com/api"),
    "bsc": ("FINSKALP_BLOCKSCOUT_BSC_URL", "https://bsc.blockscout.com/api"),
    "polygon": ("FINSKALP_BLOCKSCOUT_POLYGON_URL", "https://polygon.blockscout.com/api"),
}

_NATIVE_ASSET = {"eth": "ETH", "bsc": "BNB", "polygon": "MATIC"}


def blockscout_api_base(chain: str) -> str:
    """Resolve Blockscout REST base URL for chain (trailing /api stripped by callers)."""
    key, default = _CHAIN_CONFIG.get(chain, ("", ""))
    if not key:
        raise ValueError(f"Unsupported Blockscout chain: {chain}")
    return os.getenv(key, default).rstrip("/")


def account_txlist_url(
    chain: str,
    address: str,
    *,
    page: int = 1,
    offset: int = 50,
    api_key: str = "",
) -> str:
    base = blockscout_api_base(chain)
    addr_q = quote(address.lower() if address.startswith("0x") else address)
    key_q = f"&apikey={quote(api_key)}" if api_key else ""
    return (
        f"{base}?module=account&action=txlist&address={addr_q}"
        f"&startblock=0&endblock=99999999&page={page}&offset={offset}&sort=desc{key_q}"
    )


def account_tokentx_url(
    chain: str,
    address: str,
    *,
    page: int = 1,
    offset: int = 30,
    api_key: str = "",
) -> str:
    base = blockscout_api_base(chain)
    addr_q = quote(address.lower() if address.startswith("0x") else address)
    key_q = f"&apikey={quote(api_key)}" if api_key else ""
    return (
        f"{base}?module=account&action=tokentx&address={addr_q}"
        f"&startblock=0&endblock=99999999&page={page}&offset={offset}&sort=desc{key_q}"
    )


def parse_evm_transfers(
    chain: str,
    address: str,
    *,
    tx_body: dict[str, Any] | None,
    token_body: dict[str, Any] | None,
    native_limit: int = 50,
    token_limit: int = 30,
) -> dict[str, Any]:
    """Normalize Etherscan-compatible txlist/tokentx into FinSkalp transfer list."""
    addr = address.lower()
    native = _NATIVE_ASSET.get(chain, "NATIVE")
    txs = tx_body.get("result") if isinstance(tx_body, dict) and isinstance(tx_body.get("result"), list) else []
    token_txs = (
        token_body.get("result")
        if isinstance(token_body, dict) and isinstance(token_body.get("result"), list)
        else []
    )
    counterparties: list[str] = []
    transfers: list[dict[str, Any]] = []

    for tx in txs[:native_limit]:
        if not isinstance(tx, dict):
            continue
        frm = (tx.get("from") or "").lower()
        to = (tx.get("to") or "").lower()
        if not frm or not to:
            continue
        method = (tx.get("input") or tx.get("methodId") or "")[:10]
        transfers.append(
            {
                "from": frm,
                "to": to,
                "amount": tx.get("value"),
                "timestamp": int(tx.get("timeStamp") or 0) * 1000,
                "tx_hash": tx.get("hash", ""),
                "asset": native,
                "block_number": int(tx.get("blockNumber") or 0),
                "method_id": method,
                "contract": frm if method and method != "0x" else None,
            }
        )
        for cp in (frm, to):
            if cp and cp != addr and cp not in counterparties:
                counterparties.append(cp)

    for tx in token_txs[:token_limit]:
        if not isinstance(tx, dict):
            continue
        frm = (tx.get("from") or "").lower()
        to = (tx.get("to") or "").lower()
        transfers.append(
            {
                "from": frm,
                "to": to,
                "amount": tx.get("value"),
                "timestamp": int(tx.get("timeStamp") or 0) * 1000,
                "tx_hash": tx.get("hash", ""),
                "asset": tx.get("tokenSymbol", "ERC20"),
                "block_number": int(tx.get("blockNumber") or 0),
                "method_id": (tx.get("input") or "")[:10],
                "contract": (tx.get("contractAddress") or frm or "").lower() or None,
            }
        )
        for cp in (frm, to):
            if cp and cp != addr and cp not in counterparties:
                counterparties.append(cp)

    return {
        "chain": chain,
        "address": addr,
        "tx_count": len(txs),
        "token_tx_count": len(token_txs),
        "counterparties": counterparties[:40],
        "transfers": transfers[:60],
    }


GetJsonFn = Callable[..., Awaitable[dict[str, Any]]]


async def fetch_evm_chain_data(
    chain: str,
    address: str,
    get_json: GetJsonFn,
    *,
    source: str | None = None,
    api_key: str = "",
) -> dict[str, Any]:
    """Fetch native + token transfers via Blockscout-compatible endpoints."""
    src = source or f"blockscout_{chain}"
    addr = address.lower()
    tx_url = account_txlist_url(chain, addr, api_key=api_key)
    tx_out = await get_json(
        tx_url,
        source=src,
        cache_key=f"live:{chain}:tx:{addr}",
        category="onchain_live",
    )
    token_url = account_tokentx_url(chain, addr, api_key=api_key)
    tok_out = await get_json(
        token_url,
        source=src,
        cache_key=f"live:{chain}:token:{addr}",
        category="onchain_live",
    )
    tx_body = (tx_out.get("data") or {}) if isinstance(tx_out, dict) else {}
    token_body = (tok_out.get("data") or {}) if isinstance(tok_out, dict) else {}
    parsed = parse_evm_transfers(chain, addr, tx_body=tx_body, token_body=token_body)
    return {**tx_out, **parsed}
