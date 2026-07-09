"""
Live OSINT/blockchain collectors — реальные публичные API (без mock).

TronGrid, mempool.space, OpenSanctions, BitcoinAbuse, Maigret, Ahmia.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from urllib.parse import quote

import httpx

from flowsint_crypto_compliance.osint_core.live_cache import cache_get_json, cache_set_json
from flowsint_crypto_compliance.osint_core.live_rate_limit import await_rate_limit

_USDT_TRC20 = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
_MEMPOOL = "https://mempool.space/api"
_OPENSANCTIONS = "https://api.opensanctions.org/search/default"
_AHMIA = "https://ahmia.fi/search"
_BSCSCAN = "https://api.bscscan.com/api"
_ETH_CHAIN_ID = 1


def _etherscan_base() -> str:
    return os.getenv("ETHERSCAN_API_URL", "https://api.etherscan.io/v2/api").rstrip("/")


def _headers() -> dict[str, str]:
    h = {"User-Agent": "FinSkalp-Live/1.0 (+regulatory OSINT)"}
    tron_key = os.getenv("TRONGRID_API_KEY")
    if tron_key:
        h["TRON-PRO-API-KEY"] = tron_key
    return h


async def _get_json(url: str, *, source: str, cache_key: str, category: str) -> dict[str, Any]:
    from flowsint_crypto_compliance.infrastructure.circuit_breaker import get_breaker
    from flowsint_crypto_compliance.osint_core.scalpel.security import is_safe_external_url

    if not is_safe_external_url(url):
        return {
            "status": 0,
            "source": source,
            "error": "blocked_ssrf",
            "degraded": True,
            "url": url,
        }

    breaker = get_breaker(source)
    if not breaker.allow_request():
        return {
            "status": 503,
            "source": source,
            "degraded": True,
            "error": f"Collector {source} temporarily unavailable (circuit open)",
            "url": url,
        }

    await await_rate_limit(source)
    cached = cache_get_json(cache_key)
    if cached is not None:
        return {**cached, "_from_cache": True}

    last_err: Exception | None = None
    degraded = False
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=_headers())
            if resp.status_code == 429:
                await asyncio.sleep(2**attempt)
                continue
            data: dict[str, Any] = {
                "status": resp.status_code,
                "source": source,
                "url": url,
            }
            if resp.status_code == 200:
                try:
                    body = resp.json()
                except Exception:
                    body = {"raw": resp.text[:4000]}
                data["data"] = body
                cache_set_json(cache_key, data, category=category)
                breaker.record_success()
            else:
                data["error"] = resp.text[:500]
                if resp.status_code >= 500:
                    breaker.record_failure()
                    degraded = True
            return data
        except Exception as exc:
            last_err = exc
            breaker.record_failure()
            degraded = True
            await asyncio.sleep(2**attempt)
    return {
        "status": 0,
        "source": source,
        "error": str(last_err),
        "degraded": degraded,
    }


def _tron_collector_source() -> str:
    from flowsint_crypto_compliance.chains.on_chain_provider import get_on_chain_source_meta

    return get_on_chain_source_meta().get("on_chain_source", "trongrid")


async def collect_tron_chain(address: str) -> dict[str, Any]:
    """TRON TRX-транзакции (суверенный узел или TronGrid)."""
    from flowsint_crypto_compliance.chains.on_chain_provider import get_on_chain_source_meta
    from flowsint_crypto_compliance.chains.trongrid_client import trongrid_get

    source = _tron_collector_source()
    cache_key = f"live:tron:tx:{address}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        out = {**cached, "_from_cache": True}
    else:
        await await_rate_limit(source)
        try:
            resp = await trongrid_get(
                f"/v1/accounts/{quote(address)}/transactions",
                params={"limit": 50, "only_confirmed": "true"},
                timeout=15.0,
            )
            out: dict[str, Any] = {
                "status": resp.status_code,
                "source": source,
                "url": f"/v1/accounts/{address}/transactions",
            }
            if resp.status_code == 200:
                out["data"] = resp.json()
                cache_set_json(cache_key, out, category="onchain_live")
            else:
                out["error"] = resp.text[:500]
        except Exception as exc:
            out = {"status": 0, "source": source, "error": str(exc)}
    out.update(get_on_chain_source_meta())
    txs = (out.get("data") or {}).get("data") or []
    counterparties: list[str] = []
    edges: list[dict[str, Any]] = []
    for tx in txs:
        raw = tx.get("raw_data", {})
        contract = (raw.get("contract") or [{}])[0]
        param = contract.get("parameter", {}).get("value", {})
        frm = param.get("owner_address") or param.get("from_address")
        to = param.get("to_address")
        tx_id = tx.get("txID", "")
        ts = tx.get("block_timestamp")
        amount = param.get("amount", 0)
        if frm and to:
            edges.append(
                {
                    "from": _tron_base58(frm),
                    "to": _tron_base58(to),
                    "amount": amount,
                    "timestamp": ts,
                    "tx_hash": tx_id,
                    "asset": "TRX",
                }
            )
            for cp in (_tron_base58(frm), _tron_base58(to)):
                if cp and cp != address and cp not in counterparties:
                    counterparties.append(cp)
    return {
        **out,
        "chain": "tron",
        "address": address,
        "tx_count": len(txs),
        "counterparties": counterparties[:30],
        "transfers": edges[:50],
    }


async def _paginate_trongrid(
    path: str,
    *,
    base_params: dict[str, Any] | None = None,
    source: str,
    cache_key: str,
    max_items: int = 300,
) -> dict[str, Any]:
    """Fetch TRON REST pages using fingerprint pagination (shared rate limiter)."""
    from flowsint_crypto_compliance.chains.trongrid_client import trongrid_get

    collected: list[Any] = []
    fingerprint: str | None = None
    last_out: dict[str, Any] = {"status": 200, "source": source, "url": path}
    page_limit = min(200, max_items)
    params_base = dict(base_params or {})

    for _ in range(10):
        params = {**params_base, "limit": page_limit}
        if fingerprint:
            params["fingerprint"] = fingerprint
        cached = cache_get_json(f"{cache_key}:{len(collected)}")
        if cached is not None:
            out = {**cached, "_from_cache": True}
        else:
            await await_rate_limit(source)
            try:
                resp = await trongrid_get(path, params=params, timeout=20.0)
                data: dict[str, Any] = {
                    "status": resp.status_code,
                    "source": source,
                    "url": path,
                }
                if resp.status_code == 200:
                    data["data"] = resp.json()
                    cache_set_json(f"{cache_key}:{len(collected)}", data, category="onchain_live")
                else:
                    data["error"] = resp.text[:500]
                out = data
            except Exception as exc:
                out = {"status": 0, "source": source, "error": str(exc)}
        last_out = out
        if out.get("status") != 200:
            break
        batch = (out.get("data") or {}).get("data") or []
        collected.extend(batch)
        if len(collected) >= max_items or not batch:
            break
        fingerprint = (out.get("data") or {}).get("meta", {}).get("fingerprint")
        if not fingerprint:
            break

    return {**last_out, "items": collected[:max_items]}


async def collect_tron_account(address: str) -> dict[str, Any]:
    """Баланс TRX и TRC20 (суверенный узел или TronGrid)."""
    from flowsint_crypto_compliance.chains.on_chain_provider import get_on_chain_source_meta
    from flowsint_crypto_compliance.chains.tron import TronChainAdapter

    source = _tron_collector_source()
    try:
        state = await TronChainAdapter().get_account_state(address)
        return {
            "status": 200,
            "source": source,
            "address": address,
            **state,
            **get_on_chain_source_meta(),
        }
    except Exception as exc:
        return {
            "status": 0,
            "source": source,
            "address": address,
            "error": str(exc),
            **get_on_chain_source_meta(),
        }


async def collect_tron_trc20_transfers(address: str, *, max_transfers: int = 300) -> dict[str, Any]:
    """USDT/TRC20 переводы (с пагинацией, суверенный узел или TronGrid)."""
    from flowsint_crypto_compliance.chains.on_chain_provider import get_on_chain_source_meta

    source = _tron_collector_source()
    path = f"/v1/accounts/{quote(address)}/transactions/trc20"
    out = await _paginate_trongrid(
        path,
        base_params={"contract_address": _USDT_TRC20},
        source=source,
        cache_key=f"live:tron:trc20:{address}",
        max_items=max_transfers,
    )
    out.update(get_on_chain_source_meta())
    txs = out.get("items") or []
    counterparties: list[str] = []
    transfers: list[dict[str, Any]] = []
    for tx in txs:
        frm = tx.get("from")
        to = tx.get("to")
        transfers.append(
            {
                "from": frm,
                "to": to,
                "amount": tx.get("value"),
                "timestamp": tx.get("block_timestamp"),
                "tx_hash": tx.get("transaction_id"),
                "asset": tx.get("token_info", {}).get("symbol", "TRC20"),
            }
        )
        for cp in (frm, to):
            if cp and cp != address and cp not in counterparties:
                counterparties.append(cp)
    return {
        **out,
        "chain": "tron",
        "address": address,
        "transfer_count": len(txs),
        "counterparties": counterparties[:100],
        "transfers": transfers[:max_transfers],
        "transfer_count_full": len(txs),
    }


async def collect_btc_chain(address: str) -> dict[str, Any]:
    """mempool.space — реальные BTC-транзакции."""
    url = f"{_MEMPOOL}/address/{quote(address)}/txs"
    out = await _get_json(
        url,
        source="mempool",
        cache_key=f"live:btc:txs:{address}",
        category="onchain_live",
    )
    txs = out.get("data") if isinstance(out.get("data"), list) else []
    counterparties: list[str] = []
    transfers: list[dict[str, Any]] = []
    for tx in txs[:30]:
        txid = tx.get("txid", "")
        ts = tx.get("status", {}).get("block_time")
        for vin in tx.get("vin") or []:
            prev = (vin.get("prevout") or {}).get("scriptpubkey_address")
            if prev and prev != address:
                if prev not in counterparties:
                    counterparties.append(prev)
                transfers.append(
                    {
                        "from": prev,
                        "to": address,
                        "amount": (vin.get("prevout") or {}).get("value"),
                        "timestamp": ts,
                        "tx_hash": txid,
                        "asset": "BTC",
                    }
                )
        for vout in tx.get("vout") or []:
            nxt = vout.get("scriptpubkey_address")
            if nxt and nxt != address:
                if nxt not in counterparties:
                    counterparties.append(nxt)
                transfers.append(
                    {
                        "from": address,
                        "to": nxt,
                        "amount": vout.get("value"),
                        "timestamp": ts,
                        "tx_hash": txid,
                        "asset": "BTC",
                    }
                )
    return {
        **out,
        "chain": "btc",
        "address": address,
        "tx_count": len(txs),
        "counterparties": counterparties[:30],
        "transfers": transfers[:50],
    }


async def collect_eth_chain(address: str) -> dict[str, Any]:
    """Etherscan v2 — ETH native + ERC20 transfers."""
    api_key = os.getenv("ETHERSCAN_API_KEY", "").strip()
    key_q = f"&apikey={quote(api_key)}" if api_key else ""
    addr = address.lower()
    addr_q = quote(addr)
    base = _etherscan_base()
    tx_url = (
        f"{base}?chainid={_ETH_CHAIN_ID}&module=account&action=txlist&address={addr_q}"
        f"&startblock=0&endblock=99999999&page=1&offset=50&sort=desc{key_q}"
    )
    out = await _get_json(
        tx_url,
        source="etherscan",
        cache_key=f"live:eth:tx:{addr}",
        category="onchain_live",
    )
    body = out.get("data") or {}
    txs = body.get("result") if isinstance(body.get("result"), list) else []
    counterparties: list[str] = []
    transfers: list[dict[str, Any]] = []
    for tx in txs[:50]:
        if not isinstance(tx, dict):
            continue
        frm = (tx.get("from") or "").lower()
        to = (tx.get("to") or "").lower()
        ts = int(tx.get("timeStamp") or 0) * 1000
        amt = tx.get("value")
        tx_hash = tx.get("hash", "")
        if frm and to:
            transfers.append(
                {
                    "from": frm,
                    "to": to,
                    "amount": amt,
                    "timestamp": ts,
                    "tx_hash": tx_hash,
                    "asset": "ETH",
                }
            )
            for cp in (frm, to):
                if cp and cp != addr and cp not in counterparties:
                    counterparties.append(cp)

    token_url = (
        f"{base}?chainid={_ETH_CHAIN_ID}&module=account&action=tokentx&address={addr_q}"
        f"&startblock=0&endblock=99999999&page=1&offset=30&sort=desc{key_q}"
    )
    tok_out = await _get_json(
        token_url,
        source="etherscan",
        cache_key=f"live:eth:token:{addr}",
        category="onchain_live",
    )
    tok_body = tok_out.get("data") or {}
    token_txs = tok_body.get("result") if isinstance(tok_body.get("result"), list) else []
    for tx in token_txs[:30]:
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
            }
        )
        for cp in (frm, to):
            if cp and cp != addr and cp not in counterparties:
                counterparties.append(cp)

    return {
        **out,
        "chain": "eth",
        "address": addr,
        "tx_count": len(txs),
        "token_tx_count": len(token_txs),
        "counterparties": counterparties[:40],
        "transfers": transfers[:60],
    }


async def collect_bsc_chain(address: str) -> dict[str, Any]:
    """BscScan — BNB + BEP20 transfers (Etherscan-compatible API)."""
    api_key = os.getenv("BSCSCAN_API_KEY", "").strip()
    key_q = f"&apikey={quote(api_key)}" if api_key else ""
    addr_q = quote(address)
    tx_url = (
        f"{_BSCSCAN}?module=account&action=txlist&address={addr_q}"
        f"&startblock=0&endblock=99999999&page=1&offset=50&sort=desc{key_q}"
    )
    out = await _get_json(
        tx_url,
        source="bscscan",
        cache_key=f"live:bsc:tx:{address.lower()}",
        category="onchain_live",
    )
    body = out.get("data") or {}
    txs = body.get("result") if isinstance(body.get("result"), list) else []
    counterparties: list[str] = []
    transfers: list[dict[str, Any]] = []
    for tx in txs[:50]:
        if not isinstance(tx, dict):
            continue
        frm = (tx.get("from") or "").lower()
        to = (tx.get("to") or "").lower()
        ts = int(tx.get("timeStamp") or 0) * 1000
        amt = tx.get("value")
        tx_hash = tx.get("hash", "")
        if frm and to:
            transfers.append(
                {
                    "from": frm,
                    "to": to,
                    "amount": amt,
                    "timestamp": ts,
                    "tx_hash": tx_hash,
                    "asset": "BNB",
                }
            )
            for cp in (frm, to):
                if cp and cp != address.lower() and cp not in counterparties:
                    counterparties.append(cp)

    token_url = (
        f"{_BSCSCAN}?module=account&action=tokentx&address={addr_q}"
        f"&startblock=0&endblock=99999999&page=1&offset=30&sort=desc{key_q}"
    )
    tok_out = await _get_json(
        token_url,
        source="bscscan",
        cache_key=f"live:bsc:token:{address.lower()}",
        category="onchain_live",
    )
    tok_body = tok_out.get("data") or {}
    token_txs = tok_body.get("result") if isinstance(tok_body.get("result"), list) else []
    for tx in token_txs[:30]:
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
                "asset": tx.get("tokenSymbol", "BEP20"),
            }
        )
        for cp in (frm, to):
            if cp and cp != address.lower() and cp not in counterparties:
                counterparties.append(cp)

    return {
        **out,
        "chain": "bsc",
        "address": address,
        "tx_count": len(txs),
        "token_tx_count": len(token_txs),
        "counterparties": counterparties[:40],
        "transfers": transfers[:60],
    }


async def collect_polygon_chain(address: str) -> dict[str, Any]:
    """Polygon — Blockscout Etherscan-compatible API (MATIC + ERC20)."""
    from flowsint_crypto_compliance.chains.blockscout_client import fetch_evm_chain_data

    api_key = os.getenv("POLYGONSCAN_API_KEY", "").strip()
    return await fetch_evm_chain_data("polygon", address, _get_json, api_key=api_key)


async def collect_solana_chain(address: str) -> dict[str, Any]:
    """Solana — public JSON-RPC (rate-limited; set FINSKALP_SOLANA_RPC_URL for production)."""
    from flowsint_crypto_compliance.chains.solana import fetch_address_activity

    await await_rate_limit("solana_rpc")
    out = await fetch_address_activity(address, limit=25)
    return {
        **out,
        "chain": "solana",
        "address": address,
    }


async def collect_sanctions(query: str) -> dict[str, Any]:
    """OpenSanctions — живой поиск."""
    url = f"{_OPENSANCTIONS}?q={quote(query[:128])}&limit=10"
    out = await _get_json(
        url,
        source="opensanctions",
        cache_key=f"live:sanctions:{query[:48]}",
        category="sanctions_live",
    )
    results = (out.get("data") or {}).get("results") or []
    hits = [
        {
            "id": r.get("id"),
            "caption": r.get("caption"),
            "schema": r.get("schema"),
            "datasets": r.get("datasets"),
        }
        for r in results
    ]
    # Only flag when search result explicitly references the queried wallet address
    addr_l = query.strip().lower()
    flagged = any(
        addr_l in str(h.get("caption") or "").lower()
        or addr_l in str(h.get("id") or "").lower()
        for h in hits
    )
    return {
        **out,
        "query": query,
        "hit_count": len(hits),
        "hits": hits,
        "flagged": flagged,
    }


async def collect_bitcoinabuse(address: str) -> dict[str, Any]:
    """BitcoinAbuse — краудсорс репорты (нужен BITCOINABUSE_API_KEY)."""
    token = os.getenv("BITCOINABUSE_API_KEY", "")
    if not token:
        return {
            "status": 503,
            "source": "bitcoinabuse",
            "address": address,
            "error": "BITCOINABUSE_API_KEY not configured",
            "flagged": False,
            "reports": [],
        }
    url = f"{_BITCOINABUSE}?address={quote(address)}&api_token={quote(token)}"
    out = await _get_json(
        url,
        source="bitcoinabuse",
        cache_key=f"live:abuse:{address}",
        category="abuse_live",
    )
    data = out.get("data") or {}
    count = int(data.get("count") or data.get("report_count") or 0)
    return {
        **out,
        "address": address,
        "report_count": count,
        "flagged": count > 0,
        "reports": data.get("reports") or [],
    }


async def collect_maigret(username: str) -> dict[str, Any]:
    """Maigret — реальный скан username (subprocess)."""
    await await_rate_limit("maigret")
    cache_key = f"live:maigret:{username.lower()}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return {**cached, "_from_cache": True}

    from flowsint_crypto_compliance.osint_core.scalpel.workers.maigret_runner import run_maigret

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: run_maigret(username, top_sites=80))
    out = {
        "status": 200,
        "source": "maigret",
        "username": username,
        "profiles_found": len(result.get("sites") or []),
        "sites": (result.get("sites") or [])[:20],
        "flagged": bool(result.get("sites")),
    }
    cache_set_json(cache_key, out, category="maigret_live")
    return out


async def collect_ahmia(query: str) -> dict[str, Any]:
    """Ahmia.fi — поиск по индексу .onion (clearnet API)."""
    import re

    url = f"{_AHMIA}/?q={quote(query[:128])}"
    await await_rate_limit("ahmia")
    cached = cache_get_json(f"live:ahmia:{query[:48]}")
    if cached is not None:
        return {**cached, "_from_cache": True}

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=_headers())
        text = resp.text
        results: list[str] = []
        onion_urls: list[str] = []
        for m in re.finditer(r"https?://[a-z2-7]{16,56}\.onion[^\s\"'<>]*", text, re.I):
            u = m.group(0).rstrip(".,)")
            if u not in onion_urls:
                onion_urls.append(u)
        for m in re.finditer(r"[a-z2-7]{16,56}\.onion", text, re.I):
            u = m.group(0)
            if u not in onion_urls:
                onion_urls.append(u)
        for line in text.split("\n"):
            if ".onion" in line.lower() and len(line.strip()) > 10:
                snippet = line.strip()[:240]
                if snippet not in results:
                    results.append(snippet)
                if len(results) >= 15:
                    break
        out = {
            "status": resp.status_code,
            "source": "ahmia",
            "query": query,
            "result_count": len(results) + len(onion_urls),
            "results": results[:12],
            "onion_urls": onion_urls[:12],
            "flagged": bool(results or onion_urls),
        }
        if resp.status_code == 200:
            cache_set_json(f"live:ahmia:{query[:48]}", out, category="ahmia_live")
        return out
    except Exception as exc:
        return {"status": 0, "source": "ahmia", "query": query, "error": str(exc), "results": [], "onion_urls": []}


def _tron_base58(addr: str) -> str:
    """TronGrid иногда отдаёт hex — для demo оставляем как есть."""
    if addr.startswith("T") and len(addr) >= 30:
        return addr
    return addr


async def collect_all_live(address: str, chain: str, *, username: str | None = None) -> dict[str, Any]:
    """Параллельный сбор всех live-источников для адреса."""
    tasks: dict[str, Any] = {}
    if chain == "tron":
        tasks["tron_account"] = collect_tron_account(address)
        tasks["tron_chain"] = collect_tron_chain(address)
        tasks["tron_trc20"] = collect_tron_trc20_transfers(address)
    elif chain == "btc":
        tasks["btc_chain"] = collect_btc_chain(address)
    elif chain == "eth":
        tasks["eth_chain"] = collect_eth_chain(address)
    elif chain == "bsc":
        tasks["bsc_chain"] = collect_bsc_chain(address)
    elif chain == "polygon":
        tasks["polygon_chain"] = collect_polygon_chain(address)
    elif chain == "solana":
        tasks["solana_chain"] = collect_solana_chain(address)
    tasks["sanctions"] = collect_sanctions(address)
    if chain == "btc":
        tasks["bitcoinabuse"] = collect_bitcoinabuse(address)
    tasks["ahmia"] = collect_ahmia(address[:32])
    if username:
        tasks["maigret"] = collect_maigret(username)

    keys = list(tasks.keys())
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    merged: dict[str, Any] = {"address": address, "chain": chain, "collectors": {}}
    for key, res in zip(keys, results):
        if isinstance(res, Exception):
            merged["collectors"][key] = {"status": 0, "error": str(res)}
        else:
            merged["collectors"][key] = res
    merged["any_flagged"] = any(
        c.get("flagged") for c in merged["collectors"].values() if isinstance(c, dict)
    )
    return merged
