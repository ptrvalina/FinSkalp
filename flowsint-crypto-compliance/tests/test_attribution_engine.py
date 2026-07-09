"""Tests for autonomous attribution engine."""

from __future__ import annotations

import pytest

from flowsint_crypto_compliance.attribution.cospend_cluster import (
    build_cospend_clusters,
    propagate_cluster_labels,
)
from flowsint_crypto_compliance.attribution.entity_label_store import EntityLabelStore
from flowsint_crypto_compliance.attribution.types import EntityLabel
from flowsint_crypto_compliance.chains.base import OnChainTransfer
from flowsint_types.fiat_crypto import Chain


def test_cospend_cluster_btc_same_tx():
    transfers = [
        {"tx_hash": "tx1", "from": "addrA", "to": "hub"},
        {"tx_hash": "tx1", "from": "addrB", "to": "hub"},
    ]
    clusters = build_cospend_clusters(transfers, chain="btc")
    assert any({"addrA", "addrB"}.issubset(c) for c in clusters)


def test_cospend_propagation():
    store = {
        "addrA": EntityLabel(
            address="addrA",
            chain="tron",
            label="Binance",
            category="exchange",
            confidence=0.9,
            source="tronscan",
            tier=2,
            risk_score=12,
        )
    }
    clusters = [{"addrA", "addrB"}]
    out = propagate_cluster_labels(clusters, store, chain="tron")
    assert any(l.address == "addrB" for l in out)


@pytest.mark.asyncio
async def test_attribution_engine_labels_counterparty():
    from flowsint_crypto_compliance.attribution.attribution_engine import AttributionEngine

    store = EntityLabelStore()
    store.upsert(
        EntityLabel(
            address="TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE",
            chain="tron",
            label="Binance",
            category="exchange",
            confidence=0.85,
            source="tronscan",
            tier=2,
            risk_score=12,
        )
    )
    engine = AttributionEngine(store=store)
    engine._bootstrapped = True
    focus = "TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL"
    cp = "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE"
    inbound = [
        OnChainTransfer(
            chain=Chain.TRON,
            tx_hash="t1",
            source=cp,
            target=focus,
            asset="USDT",
            amount=500.0,
        )
    ]
    result = await engine.attribute_wallet(
        address=focus,
        chain="tron",
        inbound=inbound,
        outbound=[],
    )
    assert result.connections
    assert result.connections[0]["entity_name"] == "Binance"


def test_evidence_hash_reproducible():
    from flowsint_crypto_compliance.reporting.evidence_inventory import (
        build_evidence_inventory,
        verify_exhibit_hash,
    )

    payload = {"a": 1, "b": "test"}
    inv = build_evidence_inventory(case_ref="X", sources={"test": payload})
    assert verify_exhibit_hash(payload, inv[0]["sha256"])
