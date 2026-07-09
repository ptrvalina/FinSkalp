import pytest

from flowsint_crypto_compliance.osint_core.scalpel.entity_extractor import extract_entities
from flowsint_crypto_compliance.osint_core.scalpel.noise_filter import filter_osint_noise
from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel import ScalpelEngine
from flowsint_crypto_compliance.reporting.ocr_pipeline import OCRPipeline
from flowsint_types.fiat_crypto import Chain


def test_entity_extractor_crypto_and_inn():
    text = (
        "Кошелёк TUVHw4wBAwGEMRx2q4AXymX7FWLKXAqWJE, ИНН 7707083893, "
        "сумма 1 500 000 ₽, @otc_msk_bot, https://tronscan.org/#/address/TUV"
    )
    ex = extract_entities(text)
    assert any(a["chain"] == "tron" for a in ex.crypto_addresses)
    assert "7707083893" in ex.inn
    assert ex.usernames
    assert "tronscan.org" in ex.domains


def test_enrich_context_from_hits_domains():
    from flowsint_crypto_compliance.osint_core.scalpel.engine import _enrich_context_from_hits
    from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit

    context: dict = {"usernames": [], "domains": [], "mentions": []}
    hits = [
        OpenMentionHit(
            source_type="web",
            source_name="forum",
            title_ru="OTC @dealer_x",
            excerpt_ru="Связь через https://otc-board.example/deal",
            url="https://otc-board.example/deal",
            risk_tag="otc",
            confidence=0.6,
        )
    ]
    _enrich_context_from_hits(context, hits, {}, "TADDR")
    assert "dealer_x" in context["usernames"]
    assert "otc-board.example" in context["domains"]


def test_noise_filter_rejects_spam():
    hits = [
        OpenMentionHit(
            source_type="forum",
            source_name="spam",
            title_ru="casino bonus",
            excerpt_ru="click here 100% profit",
            url=None,
            risk_tag="spam",
            confidence=0.9,
        ),
        OpenMentionHit(
            source_type="explorer_tag",
            source_name="TronScan",
            title_ru="mixer tag",
            excerpt_ru="Публичная метка mixer для адреса",
            url="https://tronscan.org",
            risk_tag="mixer_like",
            confidence=0.72,
        ),
    ]
    res = filter_osint_noise(hits, target_address="TUVHw4wBAwGEMRx2q4AXymX7FWLKXAqWJE")
    assert len(res.kept) == 1
    assert res.kept[0].source_type == "explorer_tag"
    assert res.rejected


def test_noise_filter_blocks_leak_source():
    hits = [
        OpenMentionHit(
            source_type="leak",
            source_name="forbidden",
            title_ru="leaked db",
            excerpt_ru="stolen credentials dump",
            url=None,
            risk_tag="leak",
            confidence=0.95,
        ),
    ]
    res = filter_osint_noise(hits)
    assert len(res.kept) == 0
    assert res.rejected


def test_registry_eight_collectors():
    from flowsint_crypto_compliance.osint_core.scalpel.registry import (
        CELERY_COLLECTOR_TASKS,
        SCALPEL_COLLECTORS,
        registry_manifest,
    )

    assert len(SCALPEL_COLLECTORS) == 10
    assert len(registry_manifest()) == 10
    assert len(CELERY_COLLECTOR_TASKS) == 10


@pytest.mark.asyncio
async def test_scalpel_engine_demo_hub():
    engine = ScalpelEngine(timeout=3.0)
    st = engine.status()
    assert len(st["collectors"]) == 10
    result = await engine.collect("TRU_HUB_MSK", Chain.TRON)
    assert result.mentions
    assert result.noise_filter["quality_score"] > 0
    d = result.to_dict()
    assert d["engine"] == "FinSkalp Scalpel"
    assert "open_source_stack" in d
    assert result.osint_depth == 1


@pytest.mark.asyncio
async def test_scalpel_subset_collectors():
    engine = ScalpelEngine(timeout=3.0)
    result = await engine.collect(
        "TRU_HUB_MSK",
        Chain.TRON,
        collectors=["vasp_registry", "sanctions_watchlist"],
    )
    assert set(result.collectors_run) <= {"vasp_registry", "sanctions_watchlist"}
    with pytest.raises(ValueError, match="коллектор"):
        await engine.collect("TRU_HUB_MSK", Chain.TRON, collectors=[])


def test_ocr_pipeline_plain_text():
    ocr = OCRPipeline()
    data = (
        "Постановление суда № А40-12345/2026\n"
        "Кошелёк TUVHw4wBAwGEMRx2q4AXymX7FWLKXAqWJE\n"
        "Сумма 2 500 000 руб.\n"
    ).encode("utf-8")
    r = ocr.process_bytes(data, "seizure_order.txt")
    assert r.text_chars > 50
    assert r.seizure_fields.get("wallets")
    assert r.to_dict()["suitable_for_seizure_report"]
