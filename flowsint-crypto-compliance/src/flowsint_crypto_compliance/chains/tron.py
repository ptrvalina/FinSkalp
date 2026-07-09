from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

from flowsint_types.fiat_crypto import Chain

from .base import AddressNeighborhood, ChainAdapter, OnChainTransfer
from .trongrid_client import trongrid_get

_USDT_TRC20 = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
_DEFAULT_PAGE = 200
_MAX_PAGES = 10
_TRX_USD_ESTIMATE = float(os.getenv("FINSKALP_TRX_USD", "0.10"))


class TronChainAdapter(ChainAdapter):
    """TRON transfers via sovereign FullNode or TronGrid with pagination."""

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self._api_url = api_url or os.getenv(
            "TRONGRID_API_URL", "https://api.trongrid.io"
        )
        self._api_key = api_key or os.getenv("TRONGRID_API_KEY")

    @property
    def chain(self) -> Chain:
        return Chain.TRON

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._api_key:
            headers["TRON-PRO-API-KEY"] = self._api_key
        return headers

    async def get_neighborhood(
        self, address: str, *, depth: int = 1, limit: int = 50
    ) -> AddressNeighborhood:
        max_transfers = max(limit, 50)
        items = await self._fetch_trc20_pages(address, max_transfers=max_transfers)
        inbound: list[OnChainTransfer] = []
        outbound: list[OnChainTransfer] = []

        for item in items:
            tx = _parse_trc20(item, address)
            if not tx:
                continue
            if tx.target == address:
                inbound.append(tx)
            if tx.source == address:
                outbound.append(tx)

        return AddressNeighborhood(
            address=address, chain=self.chain, inbound=inbound, outbound=outbound
        )

    async def get_account_state(self, address: str) -> dict[str, Any]:
        """Balance TRX + TRC20 token holdings (TronGrid /v1/accounts)."""
        resp = await trongrid_get(f"/v1/accounts/{address}", timeout=15.0)
        if resp.status_code != 200:
            return {
                "balance_trx": 0.0,
                "balance_usd": 0.0,
                "token_count": 0,
                "tokens": [],
                "http_status": resp.status_code,
            }
        data = (resp.json().get("data") or [{}])[0]

        balance_sun = int(data.get("balance") or 0)
        balance_trx = balance_sun / 1_000_000
        tokens: list[dict[str, Any]] = []
        balance_usd = balance_trx * _TRX_USD_ESTIMATE

        for entry in data.get("trc20") or []:
            if not isinstance(entry, dict):
                continue
            for contract, raw_balance in entry.items():
                decimals = 6 if contract == _USDT_TRC20 else 6
                symbol = "USDT" if contract == _USDT_TRC20 else contract[:8]
                amount = int(raw_balance) / (10**decimals)
                usd = amount if symbol == "USDT" else 0.0
                balance_usd += usd
                tokens.append(
                    {
                        "symbol": symbol,
                        "contract": contract,
                        "balance": round(amount, 6),
                        "balance_usd": round(usd, 2),
                    }
                )

        return {
            "balance_trx": round(balance_trx, 6),
            "balance_usd": round(balance_usd, 2),
            "token_count": len(tokens),
            "tokens": tokens,
        }

    async def get_account_profile(self, address: str) -> dict[str, Any]:
        """Live account creation hint + balance for priority tracing."""
        state = await self.get_account_state(address)
        created_at: str | None = None
        created_note: str | None = None

        resp = await trongrid_get(f"/v1/accounts/{address}", timeout=15.0)
        if resp.status_code == 200:
            acct = (resp.json().get("data") or [{}])[0]
            raw_ct = acct.get("create_time")
            if raw_ct:
                try:
                    ts = int(raw_ct)
                    if ts > 10_000_000_000:
                        ts //= 1000
                    created_at = datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
                        "%Y-%m-%d %H:%M UTC"
                    )
                except (TypeError, ValueError, OSError):
                    pass

        if not created_at:
            earliest = await self._fetch_earliest_trc20_ts(address)
            if earliest:
                created_at = earliest
            elif state.get("http_status") == 404:
                created_note = "insufficient history to determine creation date"
            elif not state.get("tokens") and state.get("balance_trx", 0) == 0:
                created_note = "insufficient history to determine creation date"
            else:
                created_note = "insufficient history to determine creation date"

        return {
            **state,
            "created_at": created_at,
            "created_note": created_note,
        }

    async def _fetch_earliest_trc20_ts(self, address: str) -> str | None:
        resp = await trongrid_get(
            f"/v1/accounts/{address}/transactions/trc20",
            params={
                "limit": 1,
                "contract_address": _USDT_TRC20,
                "only_to": "false",
                "order_by": "block_timestamp,asc",
            },
            timeout=20.0,
        )
        if resp.status_code != 200:
            return None
        batch = resp.json().get("data") or []
        if not batch:
            return None
        raw = batch[0].get("block_timestamp")
        if not raw:
            return None
        try:
            ts = int(raw)
            if ts > 10_000_000_000:
                ts //= 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            )
        except (TypeError, ValueError, OSError):
            return None

    async def _fetch_trc20_pages(
        self, address: str, *, max_transfers: int = 200, contract: str = _USDT_TRC20
    ) -> list[dict[str, Any]]:
        page_limit = min(_DEFAULT_PAGE, max_transfers)
        collected: list[dict[str, Any]] = []
        fingerprint: str | None = None

        for _ in range(_MAX_PAGES):
            params: dict[str, Any] = {
                "only_to": "false",
                "limit": page_limit,
                "contract_address": contract,
            }
            if fingerprint:
                params["fingerprint"] = fingerprint
            resp = await trongrid_get(
                f"/v1/accounts/{address}/transactions/trc20",
                params=params,
                timeout=20.0,
            )
            if resp.status_code != 200:
                break
            body = resp.json()
            batch = body.get("data") or []
            collected.extend(batch)
            if len(collected) >= max_transfers or not batch:
                break
            fingerprint = (body.get("meta") or {}).get("fingerprint")
            if not fingerprint:
                break

        return collected[:max_transfers]


def _parse_trc20(item: dict[str, Any], focus: str) -> Optional[OnChainTransfer]:
    try:
        from_addr = item.get("from")
        to_addr = item.get("to")
        if not from_addr or not to_addr:
            return None
        token = item.get("token_info", {})
        decimals = int(token.get("decimals", 6))
        raw_value = int(item.get("value", 0))
        amount = raw_value / (10**decimals)
        return OnChainTransfer(
            chain=Chain.TRON,
            tx_hash=item.get("transaction_id", ""),
            source=from_addr,
            target=to_addr,
            asset=token.get("symbol"),
            amount=amount,
            timestamp=str(item.get("block_timestamp", "")),
        )
    except (TypeError, ValueError):
        return None
