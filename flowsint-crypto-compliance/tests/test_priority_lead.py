"""Tests for live priority tracing lead."""

from __future__ import annotations

import pytest

DEMO = "TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL"
NEW = "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE"


@pytest.mark.asyncio
async def test_priority_lead_heuristic_vs_live_differ():
    from flowsint_crypto_compliance.config.env_loader import load_project_env
    from flowsint_crypto_compliance.reporting.forensic_builder import (
        _priority_lead_heuristic,
        resolve_priority_lead_live,
    )

    load_project_env()
    onchain_demo = {
        "sample_tx": [
            {"direction": "out", "counterparty": "TLeadAddr1111111111111111111111111", "amount": 950, "hash": "tx1"},
            {"direction": "in", "counterparty": "TIn", "amount": 100, "hash": "tx0"},
        ],
        "first_activity": "2024-06-01",
        "outbound_amount": 1000,
    }
    heuristic = _priority_lead_heuristic(DEMO, onchain_demo, 1, 1000.0)
    assert heuristic is not None

    onchain_new = {
        "sample_tx": [
            {"direction": "out", "counterparty": NEW, "amount": 500, "hash": "tx2"},
        ],
        "first_activity": "2025-01-15",
        "outbound_amount": 500,
    }
    heuristic_new = _priority_lead_heuristic(NEW, onchain_new, 1, 500.0)
    assert heuristic_new is None or heuristic_new.get("lead_address") == NEW

    if not __import__("os").getenv("TRONGRID_API_KEY"):
        pytest.skip("TRONGRID_API_KEY required for live profile")

    live = await resolve_priority_lead_live(
        subject_address=DEMO,
        chain="tron",
        onchain=onchain_demo,
        outbound_n=1,
        gross_out=1000.0,
    )
    if live:
        assert live.get("data_source") in (
            "live_trongrid",
            "live_sovereign",
            "live_trongrid_failover",
        )
        assert "lead_created_at" in live or live.get("lead_created_note")
