"""Live feed and combat bootstrap tests."""

import pytest

from flowsint_crypto_compliance.demo.live_feed import live_combat_feed_event


@pytest.fixture(autouse=True)
def _combat_mode(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_COMBAT_MODE", "1")


def test_live_combat_feed_event_not_synthetic():
    row = live_combat_feed_event()
    assert row is not None
    assert row.get("source") in ("KYT_LIVE", "FinSkalp", "TX_MON", "INST_HUB")


def test_live_combat_feed_uses_metrics():
    from flowsint_crypto_compliance.demo import live_ops_metrics as lom

    lom._metrics = None
    metrics = lom.get_live_ops_metrics()
    metrics.record_screen(risk_score=77.0, address="TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE")
    row = live_combat_feed_event()
    assert row is not None
    text = row.get("text_ru", "")
    assert "77" in text or "скрининг" in text.lower() or "KYT" in text


@pytest.mark.asyncio
async def test_bootstrap_live_queue_empty_without_watchlist(monkeypatch):
    monkeypatch.delenv("FINSKALP_KYT_WATCHLIST", raising=False)
    monkeypatch.delenv("FINSKALP_COMBAT_SEED_ADDRESS", raising=False)
    from flowsint_crypto_compliance.demo import live_kyt_scanner as kyt
    from flowsint_crypto_compliance.demo.operations_center import OperationsCenter

    kyt._runtime_watchlist.clear()
    center = OperationsCenter()
    created = await center.bootstrap_live_queue()
    assert isinstance(created, list)
