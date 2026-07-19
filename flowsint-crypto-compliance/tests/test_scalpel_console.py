"""Tests for Scalpel Console catalog builder."""

from flowsint_crypto_compliance.osint_core.scalpel.console_catalog import build_scalpel_console_catalog


async def test_build_scalpel_console_catalog_shape():
    catalog = await build_scalpel_console_catalog(tor_available=False, trongrid_configured=True)
    assert "collectors" in catalog
    assert "groups" in catalog
    assert "group_order" in catalog
    assert len(catalog["collectors"]) >= 11
    sample = catalog["collectors"][0]
    for key in (
        "id",
        "name",
        "description",
        "ui_status",
        "group",
        "request_count",
        "call_history",
        "recent_errors",
    ):
        assert key in sample
    assert sample["ui_status"] in ("live", "needs_config", "in_development")
    assert "on-chain" in catalog["groups"] or "osint" in catalog["groups"]
