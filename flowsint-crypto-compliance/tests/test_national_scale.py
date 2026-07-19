import pytest

from flowsint_crypto_compliance.demo.enterprise_platform import (
    list_platform_modules,
    get_platform_overview,
)
from flowsint_crypto_compliance.demo.national_scale import (
    EXCHANGERS_REGISTRY,
    NATIONAL_METRICS,
    get_dashboard,
    list_banks,
    list_exchangers,
)


def test_national_scale_banks_and_exchangers():
    banks = list_banks(limit=100)
    assert len(banks["items"]) == 10
    assert banks["connected"] is False
    assert banks["demo_notice_ru"]
    ex = list_exchangers()
    assert ex["total"] == len(EXCHANGERS_REGISTRY)
    assert ex["total"] >= 30
    assert ex["meta"]["jurisdictions_covered"] >= 4


def test_dashboard_no_population_metric():
    d = get_dashboard()
    assert "population" not in str(d).lower() or "population_coverage" not in d
    assert d["institutions_connected"] == 10
    assert "case_pipeline" in d


def test_platform_modules_sovereign_capabilities():
    modules = list_platform_modules()
    assert len(modules) >= 10
    tags = {m["capability_tag_ru"] for m in modules}
    assert all(tag for tag in tags)
    assert all(m.get("status_ru") for m in modules)
    blob = " ".join(tags).lower()
    for vendor in ("chainalysis", "elliptic", "trm", "sumsub", "lseg", "world-check"):
        assert vendor not in blob


def test_platform_overview_sovereign_sources():
    overview = get_platform_overview()
    assert overview["platform_name_ru"] == "Flowsint Compliance"
    assert len(overview["integrations"]) >= 7
    blob = str(overview["integrations"]).lower()
    for vendor in ("chainalysis", "elliptic", "trm", "sumsub", "lseg"):
        assert vendor not in blob
