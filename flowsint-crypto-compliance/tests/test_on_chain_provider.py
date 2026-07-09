"""Tests for OnChainProvider failover and sovereign routing."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from flowsint_crypto_compliance.chains.on_chain_provider import (
    FailoverOnChainProvider,
    SovereignTronProvider,
    TronGridProvider,
    get_on_chain_source_meta,
    get_tron_provider,
    reset_tron_provider,
)


def _resp(status: int = 200, body: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status,
        json=body or {"ok": True},
        request=httpx.Request("GET", "http://test"),
    )


@pytest.fixture(autouse=True)
def _reset_provider():
    reset_tron_provider()
    yield
    reset_tron_provider()


@pytest.mark.asyncio
async def test_failover_uses_sovereign_when_healthy():
    sovereign = SovereignTronProvider("http://sovereign:8090")
    trongrid = TronGridProvider("https://api.trongrid.io")
    failover = FailoverOnChainProvider(sovereign=sovereign, trongrid=trongrid)

    with patch.object(
        failover, "_sovereign_available", new=AsyncMock(return_value=True)
    ), patch.object(
        sovereign, "get", new=AsyncMock(return_value=_resp(200, {"data": []}))
    ) as sovereign_get, patch.object(
        trongrid, "get", new=AsyncMock(return_value=_resp(200, {"data": []}))
    ) as trongrid_get:
        resp = await failover.get("/v1/accounts/TTest")

    assert resp.status_code == 200
    sovereign_get.assert_awaited_once()
    trongrid_get.assert_not_awaited()
    assert failover.last_provider_used.is_sovereign is True
    assert failover.provider_label_ru == "данные с суверенного узла FinSkalp"


@pytest.mark.asyncio
async def test_failover_falls_back_to_trongrid_when_sovereign_down():
    sovereign = SovereignTronProvider("http://sovereign:8090")
    trongrid = TronGridProvider("https://api.trongrid.io")
    failover = FailoverOnChainProvider(sovereign=sovereign, trongrid=trongrid)

    with patch.object(
        failover, "_sovereign_available", new=AsyncMock(return_value=False)
    ), patch.object(
        trongrid, "get", new=AsyncMock(return_value=_resp(200, {"data": [{"x": 1}]}))
    ) as trongrid_get:
        resp = await failover.get("/v1/accounts/TTest")

    assert resp.status_code == 200
    trongrid_get.assert_awaited_once()
    assert failover.last_provider_used.is_sovereign is False
    assert failover.provider_label_ru == "TronGrid (failover)"


@pytest.mark.asyncio
async def test_failover_on_sovereign_5xx_uses_trongrid():
    sovereign = SovereignTronProvider("http://sovereign:8090")
    trongrid = TronGridProvider("https://api.trongrid.io")
    failover = FailoverOnChainProvider(sovereign=sovereign, trongrid=trongrid)

    with patch.object(
        failover, "_sovereign_available", new=AsyncMock(return_value=True)
    ), patch.object(sovereign, "get", new=AsyncMock(return_value=_resp(503))), patch.object(
        trongrid, "get", new=AsyncMock(return_value=_resp(200, {"data": []}))
    ):
        await failover.get("/v1/accounts/TTest")

    assert failover.provider_label_ru == "TronGrid (failover)"


@pytest.mark.asyncio
async def test_trongrid_get_delegates_to_provider(monkeypatch):
    monkeypatch.setenv("FINSKALP_TRON_PROVIDER", "trongrid")
    reset_tron_provider()
    provider = get_tron_provider()
    assert provider.provider_id == "trongrid"

    with patch.object(provider, "get", new=AsyncMock(return_value=_resp(200))) as mock_get:
        from flowsint_crypto_compliance.chains.trongrid_client import trongrid_get

        await trongrid_get("/v1/accounts/TTest", timeout=5.0)
        mock_get.assert_awaited()


def test_on_chain_source_meta_reflects_last_provider():
    sovereign = SovereignTronProvider("http://sovereign:8090")
    failover = FailoverOnChainProvider(sovereign=sovereign, trongrid=TronGridProvider())
    failover._last_used = sovereign  # noqa: SLF001

    with patch(
        "flowsint_crypto_compliance.chains.on_chain_provider.get_tron_provider",
        return_value=failover,
    ):
        meta = get_on_chain_source_meta()

    assert meta["on_chain_is_sovereign"] is True
    assert "суверенного узла" in meta["on_chain_source_ru"]


@pytest.mark.asyncio
async def test_probe_sovereign_node_v1_accounts():
    from flowsint_crypto_compliance.chains.on_chain_provider import probe_sovereign_node

    async def fake_get(url, **kwargs):
        return httpx.Response(200, json={"data": []}, request=httpx.Request("GET", url))

    async def fake_post(url, **kwargs):
        body = {"block_header": {"raw_data": {"number": 12345678}}}
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    mock_client = AsyncMock()
    mock_client.get = fake_get
    mock_client.post = fake_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        ok, height = await probe_sovereign_node("http://127.0.0.1:8090")

    assert ok is True
    assert height == 12345678
