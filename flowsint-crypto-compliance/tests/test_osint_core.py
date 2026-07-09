import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from flowsint_crypto_compliance.chains.base import InMemoryChainAdapter, OnChainTransfer
from flowsint_crypto_compliance.ingestion.bank_regulator import FileBankRegulatorConnector
from flowsint_crypto_compliance.ingestion.pipeline import IngestPipeline
from flowsint_crypto_compliance.osint_core.fusion_engine import OSINTFusionEngine
from flowsint_types.fiat_crypto import (
    Chain,
    ControlPurchaseEvent,
    LicensedPlatformEvent,
    RegistrySource,
    SovereignRiskLabel,
)


@pytest.fixture
def case_fixtures(tmp_path: Path):
    bank_path = tmp_path / "banks.jsonl"
    bank_path.write_text(
        json.dumps(
            {
                "feed_id": "b1",
                "bank_name": "Sber",
                "region": "RU",
                "currency": "RUB",
                "amount": 100000,
                "subject_id": "subj-1",
                "case_id": "case-42",
                "alert_type": "crypto_suspicion",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    licensed_path = tmp_path / "vasp.jsonl"
    licensed_path.write_text(
        json.dumps(
            {
                "event_id": "v1",
                "platform_name": "LocalVASP",
                "region": "RU",
                "direction": "deposit",
                "chain": "tron",
                "address": "TWalletRU",
                "amount_fiat": 98000,
                "asset": "USDT",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(
        json.dumps(
            {
                "label_id": "k1",
                "source": "internal_osint",
                "chain": "tron",
                "address": "TWalletRU",
                "entity_name": "Серый OTC-узел",
                "category": "otc",
                "confidence": 0.8,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "bank_path": bank_path,
        "licensed_path": licensed_path,
        "registry_path": registry_path,
    }


@pytest.mark.asyncio
async def test_full_fusion_pipeline_bank_registry_sovereign(case_fixtures):
    transfers = [
        OnChainTransfer(Chain.TRON, "tx1", "TGray", "TWalletRU", "USDT", 1000),
    ]
    adapters = {Chain.TRON: InMemoryChainAdapter(Chain.TRON, transfers)}
    engine = OSINTFusionEngine(chain_adapters=adapters)
    pipeline = IngestPipeline(engine)

    bundle = pipeline.build_bundle(
        "case-42",
        bank_connector=FileBankRegulatorConnector(case_fixtures["bank_path"]),
        licensed_path=case_fixtures["licensed_path"],
        control_path=None,
        registry_path=case_fixtures["registry_path"],
    )
    bundle.control_purchases = [
        ControlPurchaseEvent(
            event_id="cp1",
            operator_ref="u1",
            region="RU",
            channel="p2p_rub",
            chain=Chain.TRON,
            target_address="TGray",
        )
    ]

    result = await engine.fuse(bundle)

    assert result.case_id == "case-42"
    assert len(result.graph.nodes) >= 4
    assert result.attributions

    wallet_attr = next(a for a in result.attributions if a.address == "TWalletRU")
    assert wallet_attr.primary_region == "RU"
    assert wallet_attr.watchlist_label == "Серый OTC-узел"
    assert wallet_attr.linkage_strength is not None
    assert wallet_attr.linkage_strength >= 0.5
    assert wallet_attr.bank_feed_ids == ["b1"]
    assert any("registry:" in e for e in (wallet_attr.evidence_chain or []))


@pytest.mark.asyncio
async def test_domestic_wins_over_disputed_registry(case_fixtures):
    engine = OSINTFusionEngine()
    bundle = pipeline_bundle_with_disputed_registry()
    result = await engine.fuse(bundle)
    attr = next(a for a in result.attributions if a.address == "TAddrX")
    assert attr.disputed is True
    assert any("domestic_wins" in e for e in (attr.evidence_chain or []))


def pipeline_bundle_with_disputed_registry():
    from flowsint_crypto_compliance.osint_core.fusion_engine import InvestigationBundle

    return InvestigationBundle(
        case_id="dispute-1",
        fiat_events=[],
        licensed_events=[],
        control_purchases=[
            ControlPurchaseEvent(
                event_id="cp9",
                operator_ref="u9",
                region="RU",
                channel="otc_telegram",
                chain=Chain.TRON,
                target_address="TAddrX",
            )
        ],
        registry_labels=[
            SovereignRiskLabel(
                label_id="kd1",
                source=RegistrySource.CIS_PARTNER,
                chain=Chain.TRON,
                address="TAddrX",
                entity_name="Зарубежная биржа",
                category="exchange",
                confidence=0.9,
                disputed=True,
            )
        ],
    )


def test_label_cache_keeps_highest_confidence():
    from flowsint_crypto_compliance.storage.label_cache import LabelCache

    cache = LabelCache()
    low = SovereignRiskLabel(
        label_id="a",
        source=RegistrySource.CIS_PARTNER,
        chain=Chain.TRON,
        address="TX",
        entity_name="Low",
        confidence=0.4,
    )
    high = SovereignRiskLabel(
        label_id="b",
        source=RegistrySource.INTERNAL_OSINT,
        chain=Chain.TRON,
        address="TX",
        entity_name="High",
        confidence=0.9,
    )
    cache.put(low)
    cache.put(high)
    assert cache.lookup(Chain.TRON, "TX").entity_name == "High"
