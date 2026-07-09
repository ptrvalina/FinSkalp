"""Tests for KYT exposure engine."""

from __future__ import annotations

from flowsint_crypto_compliance.chains.base import OnChainTransfer
from flowsint_crypto_compliance.engine.exposure_engine import compute_exposure
from flowsint_types.fiat_crypto import Chain, RegistrySource, SovereignRiskLabel


def _label(addr: str, entity: str, category: str, score: float = 20.0) -> SovereignRiskLabel:
    return SovereignRiskLabel(
        label_id=f"l-{addr[:8]}",
        source=RegistrySource.INTERNAL_OSINT,
        chain=Chain.TRON,
        address=addr,
        entity_name=entity,
        category=category,
        risk_score=score,
        confidence=0.9,
    )


def test_compute_exposure_direct_counterparty():
    focus = "TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL"
    cp = "TBybitExample1234567890123456789012"
    labels = {cp: _label(cp, "Bybit", "exchange", 10)}

    inbound = [
        OnChainTransfer(
            chain=Chain.TRON,
            tx_hash="tx1",
            source=cp,
            target=focus,
            asset="USDT",
            amount=1000.0,
        )
    ]
    result = compute_exposure(
        focus_address=focus,
        chain=Chain.TRON,
        inbound=inbound,
        outbound=[],
        label_lookup=lambda a: labels.get(a),
    )
    assert result.connection_count == 1
    assert result.source_of_funds["low"] == 100.0
    assert result.indirect_exposure[0]["entity_name"] == "Bybit"


def test_imported_exposure_overrides():
    focus = "TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL"
    imported = [
        {
            "entity_name": "Stake",
            "category": "gambling",
            "risk_pct": 75,
            "hops": 3,
            "amount": 500.0,
            "behavior": "indirect",
            "risk_tier": "high",
        },
        {
            "entity_name": "Binance",
            "category": "exchange",
            "risk_pct": 10,
            "hops": 2,
            "amount": 9500.0,
            "behavior": "indirect",
            "risk_tier": "low",
        },
    ]
    result = compute_exposure(
        focus_address=focus,
        chain=Chain.TRON,
        inbound=[],
        outbound=[],
        label_lookup=lambda a: None,
        imported_exposure=imported,
    )
    assert result.source_of_funds["low"] == 95.0
    assert result.source_of_funds["high"] == 5.0
    assert len(result.indirect_exposure) == 2
