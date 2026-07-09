from __future__ import annotations

import pytest

from flowsint_crypto_compliance.platform.v2.integration.status import (
    get_integration_status,
    render_status_markdown_table,
)
from flowsint_crypto_compliance.platform.v2.integration import smoke as smoke_mod


def test_integration_status_structure(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_COMBAT_MODE", "0")
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")
    monkeypatch.delenv("TRONGRID_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    status = get_integration_status()

    assert status["ok"] is True
    assert status["combat_mode"] is False
    assert status["entity_store"] == "memory"
    assert [item["component"] for item in status["items"]] == [
        "blockchain",
        "ICF",
        "CRIF",
        "RDE",
        "ECCF",
        "EIA",
        "ASPP",
        "ESA",
        "IDOO",
        "EGPR",
        "KG",
        "event bus",
        "celery",
    ]
    for item in status["items"]:
        assert set(item) == {"component", "status", "real_data", "needs_external"}
        assert item["status"] in {"working", "stub", "partial"}
        assert item["real_data"] in {"yes", "no", "partial"}
        assert isinstance(item["needs_external"], list)

    table = render_status_markdown_table(status)
    assert "Компонент" in table
    assert "| blockchain |" in table


@pytest.mark.asyncio
async def test_run_live_smoke_memory_mode(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_COMBAT_MODE", "0")
    monkeypatch.setenv("FINSKALP_ENTITY_STORE", "memory")

    async def fake_analyze_blockchain_address(**kwargs):
        return {"ok": True, "kind": "blockchain", **kwargs}

    async def fake_run_icf_collect(**kwargs):
        return {"ok": True, "kind": "icf", **kwargs}

    async def fake_run_crif_check(**kwargs):
        return {"ok": True, "kind": "crif", **kwargs}

    async def fake_acquire_platform_signals(**kwargs):
        return {
            "blockchain_signals": {"chain": "tron", "transaction_count": 3},
            "registry_signals": {"sanctioned": False},
            "_signal_bridge": {"auto_acquired": ["blockchain_signals", "registry_signals"]},
        }

    async def fake_run_rde_assess(**kwargs):
        return {"ok": True, "kind": "rde", **kwargs}

    async def fake_register_eccf_evidence(**kwargs):
        return {"ok": True, "kind": "eccf", **kwargs}

    monkeypatch.setattr(smoke_mod, "analyze_blockchain_address", fake_analyze_blockchain_address)
    monkeypatch.setattr(smoke_mod, "run_icf_collect", fake_run_icf_collect)
    monkeypatch.setattr(smoke_mod, "run_crif_check", fake_run_crif_check)
    monkeypatch.setattr(smoke_mod, "acquire_platform_signals", fake_acquire_platform_signals)
    monkeypatch.setattr(smoke_mod, "run_rde_assess", fake_run_rde_assess)
    monkeypatch.setattr(smoke_mod, "register_eccf_evidence", fake_register_eccf_evidence)

    result = await smoke_mod.run_live_smoke(
        case_ref="SMOKE-001",
        address="T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb",
        chain="tron",
    )

    assert result["ok"] is True
    assert result["combat_mode"] is False
    assert [step["step"] for step in result["steps"]] == [
        "blockchain",
        "icf",
        "crif",
        "signal_bridge",
        "rde",
        "eccf",
    ]
    assert result["steps"][1]["mode"] == "stub"
    assert result["steps"][3]["result"]["auto_acquired"] == [
        "blockchain_signals",
        "registry_signals",
    ]
