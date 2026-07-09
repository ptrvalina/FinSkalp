"""TRON on-chain data providers — sovereign java-tron FullNode with TronGrid failover."""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from flowsint_crypto_compliance.chains.trongrid_client import trongrid_headers

_DEFAULT_SOVEREIGN_URL = "http://127.0.0.1:8090"
_DEFAULT_TRONGRID_URL = "https://api.trongrid.io"
_HEALTH_PROBE_ACCOUNT = "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"
_SOVEREIGN_OK_TTL_SEC = 30.0
_SOVEREIGN_FAIL_TTL_SEC = 15.0

_provider_singleton: "OnChainProvider | None" = None


class OnChainProvider(ABC):
    """Abstract TRON REST provider (TronGrid-compatible paths)."""

    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @property
    @abstractmethod
    def provider_label_ru(self) -> str: ...

    @property
    @abstractmethod
    def is_sovereign(self) -> bool: ...

    @abstractmethod
    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        timeout: float = 20.0,
    ) -> httpx.Response: ...


class _BaseHttpProvider(OnChainProvider):
    def __init__(self, base_url: str, *, use_trongrid_key: bool = False) -> None:
        self._base_url = base_url.rstrip("/")
        self._use_trongrid_key = use_trongrid_key

    def _build_url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return f"{self._base_url}/{path.lstrip('/')}"

    def _headers(self) -> dict[str, str]:
        if self._use_trongrid_key:
            return trongrid_headers()
        return {"User-Agent": "FinSkalp-Live/1.0 (+regulatory OSINT)"}

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        timeout: float = 20.0,
    ) -> httpx.Response:
        url = self._build_url(path)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            return await client.get(url, headers=self._headers(), params=params)


class TronGridProvider(_BaseHttpProvider):
    provider_id = "trongrid"
    provider_label_ru = "TronGrid"

    @property
    def is_sovereign(self) -> bool:
        return False

    def __init__(self, api_url: str | None = None) -> None:
        super().__init__(
            api_url or os.getenv("TRONGRID_API_URL", _DEFAULT_TRONGRID_URL),
            use_trongrid_key=True,
        )


class SovereignTronProvider(_BaseHttpProvider):
    provider_id = "sovereign"
    provider_label_ru = "данные с суверенного узла FinSkalp"

    @property
    def is_sovereign(self) -> bool:
        return True

    def __init__(self, base_url: str | None = None) -> None:
        super().__init__(
            base_url or os.getenv("FINSKALP_TRON_SOVEREIGN_URL", _DEFAULT_SOVEREIGN_URL),
            use_trongrid_key=False,
        )


class FailoverOnChainProvider(OnChainProvider):
    """Try sovereign FullNode first; fall back to TronGrid when unavailable."""

    provider_id = "failover"

    def __init__(
        self,
        sovereign: SovereignTronProvider | None = None,
        trongrid: TronGridProvider | None = None,
    ) -> None:
        self._sovereign = sovereign or SovereignTronProvider()
        self._trongrid = trongrid or TronGridProvider()
        self._last_used: OnChainProvider = self._trongrid
        self._used_failover = False
        self._sovereign_ok_until = 0.0
        self._sovereign_fail_until = 0.0

    @property
    def last_provider_used(self) -> OnChainProvider:
        return self._last_used

    @property
    def provider_label_ru(self) -> str:
        if self._last_used.is_sovereign:
            return self._last_used.provider_label_ru
        if self._used_failover:
            return "TronGrid (failover)"
        return self._trongrid.provider_label_ru

    @property
    def is_sovereign(self) -> bool:
        return self._last_used.is_sovereign

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        timeout: float = 20.0,
    ) -> httpx.Response:
        self._used_failover = False
        if await self._sovereign_available():
            try:
                resp = await self._sovereign.get(path, params=params, timeout=timeout)
                if resp.status_code != 429 and resp.status_code < 500:
                    self._last_used = self._sovereign
                    self._mark_sovereign_ok()
                    return resp
            except (httpx.HTTPError, OSError):
                self._mark_sovereign_down()
            except Exception:
                self._mark_sovereign_down()

        self._used_failover = True
        resp = await self._trongrid.get(path, params=params, timeout=timeout)
        self._last_used = self._trongrid
        return resp

    async def _sovereign_available(self) -> bool:
        now = time.monotonic()
        if now < self._sovereign_fail_until:
            return False
        if now < self._sovereign_ok_until:
            return True
        ok, _ = await probe_sovereign_node(self._sovereign._base_url)
        if ok:
            self._mark_sovereign_ok()
        else:
            self._mark_sovereign_down()
        return ok

    def _mark_sovereign_ok(self) -> None:
        self._sovereign_ok_until = time.monotonic() + _SOVEREIGN_OK_TTL_SEC
        self._sovereign_fail_until = 0.0

    def _mark_sovereign_down(self) -> None:
        self._sovereign_fail_until = time.monotonic() + _SOVEREIGN_FAIL_TTL_SEC
        self._sovereign_ok_until = 0.0


def get_tron_provider() -> OnChainProvider:
    """Singleton factory — ``FINSKALP_TRON_PROVIDER=failover|trongrid|sovereign``."""
    global _provider_singleton
    if _provider_singleton is None:
        mode = os.getenv("FINSKALP_TRON_PROVIDER", "failover").strip().lower()
        if mode == "sovereign":
            _provider_singleton = SovereignTronProvider()
        elif mode == "trongrid":
            _provider_singleton = TronGridProvider()
        else:
            _provider_singleton = FailoverOnChainProvider()
    return _provider_singleton


def reset_tron_provider() -> None:
    """Clear singleton (tests)."""
    global _provider_singleton
    _provider_singleton = None


def active_on_chain_provider() -> OnChainProvider:
    """Provider that served the last request (failover tracks actual backend)."""
    provider = get_tron_provider()
    if isinstance(provider, FailoverOnChainProvider):
        return provider.last_provider_used
    return provider


def get_on_chain_source_meta() -> dict[str, Any]:
    """Metadata for screening reports and forensic enrichment."""
    active = active_on_chain_provider()
    failover = isinstance(get_tron_provider(), FailoverOnChainProvider)
    used_failover = failover and not active.is_sovereign
    return {
        "on_chain_source": active.provider_id,
        "on_chain_source_ru": (
            "TronGrid (failover)" if used_failover else active.provider_label_ru
        ),
        "on_chain_is_sovereign": active.is_sovereign,
        "on_chain_failover": used_failover,
    }


async def probe_sovereign_node(
    base_url: str | None = None,
    *,
    timeout: float = 3.0,
) -> tuple[bool, int | None]:
    """Quick health check — TronGrid-compatible GET or ``/wallet/getnowblock``."""
    url = (base_url or os.getenv("FINSKALP_TRON_SOVEREIGN_URL", _DEFAULT_SOVEREIGN_URL)).rstrip(
        "/"
    )
    headers = {"User-Agent": "FinSkalp-Live/1.0 (+regulatory OSINT)"}
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(
                f"{url}/v1/accounts/{_HEALTH_PROBE_ACCOUNT}",
                headers=headers,
            )
            if resp.status_code in (200, 404):
                height = await _fetch_block_height(client, url, headers=headers)
                return True, height
            resp = await client.post(f"{url}/wallet/getnowblock", headers=headers, json={})
            if resp.status_code == 200:
                return True, _block_number_from_wallet(resp.json())
    except (httpx.HTTPError, OSError, ValueError):
        pass
    return False, None


async def probe_sovereign_sync_state(
    base_url: str | None = None,
    *,
    timeout: float = 4.0,
) -> dict[str, Any]:
    """Snapshot / sync gate for java-tron — used before marking sovereign active."""
    url = (base_url or os.getenv("FINSKALP_TRON_SOVEREIGN_URL", _DEFAULT_SOVEREIGN_URL)).rstrip(
        "/"
    )
    min_height = int(os.getenv("FINSKALP_TRON_SNAPSHOT_MIN_HEIGHT", "70000000"))
    reachable, block_height = await probe_sovereign_node(url, timeout=timeout)
    sync_state = "unreachable"
    peer_count: int | None = None
    if reachable:
        headers = {"User-Agent": "FinSkalp-Live/1.0 (+regulatory OSINT)"}
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.post(f"{url}/wallet/getnodeinfo", headers=headers, json={})
                if resp.status_code == 200:
                    info = resp.json() or {}
                    peers = info.get("peerList") or info.get("peer_list") or []
                    peer_count = len(peers) if isinstance(peers, list) else None
        except (httpx.HTTPError, OSError, ValueError):
            pass
        if block_height is not None and block_height >= min_height:
            sync_state = "ready"
        else:
            sync_state = "syncing"
    gate_passed = reachable and sync_state == "ready"
    return {
        "snapshot_sync_state": sync_state,
        "snapshot_min_height": min_height,
        "snapshot_gate_passed": gate_passed,
        "sovereign_peer_count": peer_count,
    }


async def _fetch_block_height(
    client: httpx.AsyncClient,
    base_url: str,
    *,
    headers: dict[str, str],
) -> int | None:
    try:
        resp = await client.post(f"{base_url}/wallet/getnowblock", headers=headers, json={})
        if resp.status_code == 200:
            return _block_number_from_wallet(resp.json())
    except (httpx.HTTPError, OSError, ValueError):
        pass
    return None


def _block_number_from_wallet(body: dict[str, Any]) -> int | None:
    raw = (body.get("block_header") or {}).get("raw_data") or {}
    num = raw.get("number")
    return int(num) if num is not None else None


async def tron_infra_status() -> dict[str, Any]:
    """Status payload for ``GET /api/infra/tron-node`` and health CLI."""
    sovereign_url = os.getenv("FINSKALP_TRON_SOVEREIGN_URL", _DEFAULT_SOVEREIGN_URL)
    mode = os.getenv("FINSKALP_TRON_PROVIDER", "failover").strip().lower()
    reachable, block_height = await probe_sovereign_node(sovereign_url)
    sync = await probe_sovereign_sync_state(sovereign_url)
    active = active_on_chain_provider()
    failover = isinstance(get_tron_provider(), FailoverOnChainProvider)
    return {
        "provider_mode": mode,
        "sovereign_url": sovereign_url,
        "sovereign_reachable": reachable,
        "sovereign_block_height": block_height,
        **sync,
        "active_provider_id": active.provider_id,
        "active_provider_label_ru": (
            "TronGrid (failover)"
            if failover and not active.is_sovereign
            else active.provider_label_ru
        ),
        "active_is_sovereign": active.is_sovereign,
        "failover_enabled": mode == "failover",
    }
