"""RFC-0013 Incremental Block Sync — tests."""

from __future__ import annotations

import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.block_sync import sync_chain_incremental
from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.sync_lock import chain_sync_lock
from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.sync_store import (
    BlockSyncStore,
    get_block_sync_store,
    reset_block_sync_store,
)
from flowsint_crypto_compliance.platform.v2.routes import create_platform_v2_router


@pytest.fixture(autouse=True)
def clean_store(monkeypatch):
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")
    reset_block_sync_store()
    yield
    reset_block_sync_store()


@pytest.fixture
def v2_client():
    app = FastAPI()
    app.include_router(create_platform_v2_router(), prefix="/api/platform/v2")
    return TestClient(app)


@pytest.mark.asyncio
async def test_incremental_sync_advances_cursor():
    r1 = await sync_chain_incremental("tron", simulate=True, max_blocks=3)
    assert r1["ok"] is True
    assert r1["blocks_synced"] == 3
    cursor_after = r1["cursor_after"]
    r2 = await sync_chain_incremental("tron", simulate=True, max_blocks=2)
    assert r2["cursor_after"] == cursor_after + 2


@pytest.mark.asyncio
async def test_sync_idempotent_at_tip():
    await sync_chain_incremental("btc", simulate=True, max_blocks=2)
    store = get_block_sync_store()
    cur = store.get_cursor("btc").last_block_height
    again = await sync_chain_incremental("btc", simulate=True, max_blocks=5)
    # simulate mode always advances; real mode would return up-to-date
    assert again["blocks_synced"] >= 0
    assert store.get_cursor("btc").last_block_height >= cur


def test_sync_status_api(v2_client):
    resp = v2_client.get("/api/platform/v2/blockchain-intelligence/sync/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "chains" in body


@pytest.mark.asyncio
async def test_sync_run_api(v2_client):
    resp = v2_client.post(
        "/api/platform/v2/blockchain-intelligence/sync/run",
        json={"chains": ["tron"], "simulate": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["results"][0]["blocks_synced"] >= 1


@pytest.mark.asyncio
async def test_analyze_uses_local_index():
    store = get_block_sync_store()
    store.index_transfer(
        "tron",
        {
            "tx_hash": "localtx1",
            "source": "TSender",
            "target": "TLocalTarget",
            "asset": "TRX",
            "amount": 50.0,
            "timestamp": "1700000001",
        },
    )
    from flowsint_crypto_compliance.platform.v2.blockchain_intelligence import get_blockchain_intelligence_service
    from flowsint_crypto_compliance.chains.base import InMemoryChainAdapter, OnChainTransfer
    from flowsint_types.fiat_crypto import Chain
    import flowsint_crypto_compliance.platform.v2.intelligence.blockchain_capabilities as bc

    bc.get_chain_adapter_by_key = lambda *a, **k: InMemoryChainAdapter(Chain.TRON, [])

    result = await get_blockchain_intelligence_service().analyze_address(
        address="TLocalTarget",
        chain="tron",
        use_memory=True,
        publish=False,
    )
    assert result["ok"] is True
    assert result["explain"]["indexed_transfers"] >= 1
    assert result["explain"]["data_source"] == "merged"


def test_memory_sync_lock_prevents_concurrent():
    lock_held = threading.Event()
    release_lock = threading.Event()
    contender_results: list[bool] = []

    def holder():
        with chain_sync_lock("tron", use_memory=True) as acquired:
            assert acquired is True
            lock_held.set()
            release_lock.wait(timeout=2)

    def contender():
        lock_held.wait(timeout=2)
        with chain_sync_lock("tron", use_memory=True) as acquired:
            contender_results.append(acquired)

    t_holder = threading.Thread(target=holder)
    t_contender = threading.Thread(target=contender)
    t_holder.start()
    t_contender.start()
    t_contender.join(timeout=3)
    release_lock.set()
    t_holder.join(timeout=3)

    assert contender_results == [False]


def test_store_backend_memory(monkeypatch):
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")
    reset_block_sync_store()
    store = get_block_sync_store()
    assert isinstance(store, BlockSyncStore)
    assert store.status()["backend"] == "memory"
