import pytest

from flowsint_crypto_compliance.chains.base import AddressNeighborhood, OnChainTransfer
from flowsint_crypto_compliance.cis.coverage import CIS_CORRIDORS
from flowsint_crypto_compliance.engine.corridor_analyzer import CorridorAnalyzer
from flowsint_crypto_compliance.engine.sovereign_attributor import SovereignAttributor
from flowsint_crypto_compliance.heuristics.black_zone import BlackZoneAnalyzer, HubDetector
from flowsint_types.fiat_crypto import (
    Chain,
    ControlPurchaseEvent,
    CryptoCluster,
    EntityKind,
    EvidenceSource,
    FiatLegEvent,
    LicensedPlatformEvent,
)


def test_corridor_matches_ru_kz_tr_pattern():
    analyzer = CorridorAnalyzer()
    match = analyzer.best_corridor(["RU", "KZ", "TR"])
    assert match is not None
    assert "RU" in match.matched_regions
    assert "TR" in match.matched_regions
    assert match.confidence >= 0.5


def test_hub_detector_flags_high_counterparty_address():
    txs = []
    for i in range(12):
        txs.append(
            OnChainTransfer(
                chain=Chain.TRON,
                tx_hash=f"in{i}",
                source=f"TPeerIn{i}",
                target="THub",
                asset="USDT",
                amount=1000,
            )
        )
        txs.append(
            OnChainTransfer(
                chain=Chain.TRON,
                tx_hash=f"out{i}",
                source="THub",
                target=f"TPeerOut{i}",
                asset="USDT",
                amount=1000,
            )
        )

    neighborhood = AddressNeighborhood(
        address="THub",
        chain=Chain.TRON,
        inbound=txs[0::2],
        outbound=txs[1::2],
    )
    hub = HubDetector(min_counterparties=8)
    score = hub.score(neighborhood)

    assert hub.is_hub(neighborhood)
    assert "high_fan_in_fan_out" in score.signals
    assert score.score >= 0.65


def test_black_zone_analyzer_without_kyt_labels():
    neighborhood = AddressNeighborhood(
        address="TLayer",
        chain=Chain.TRON,
        inbound=[
            OnChainTransfer(Chain.TRON, "t1", "TA", "TLayer", "USDT", 5000),
            OnChainTransfer(Chain.TRON, "t2", "TB", "TLayer", "USDT", 5000),
        ],
        outbound=[
            OnChainTransfer(Chain.TRON, "t3", "TLayer", "TX1", "USDT", 5000),
            OnChainTransfer(Chain.TRON, "t4", "TLayer", "TX2", "USDT", 5000),
            OnChainTransfer(Chain.TRON, "t5", "TLayer", "TX3", "USDT", 5000),
        ],
    )
    assessment = BlackZoneAnalyzer().assess(neighborhood)
    assert assessment.risk_score > 0
    assert assessment.likely_role in ("layering", "hub", "mixer_like")


def test_sovereign_attributor_uses_only_domestic_evidence():
    attributor = SovereignAttributor()

    weights = attributor.ingest_domestic_context(
        fiat_events=[
            FiatLegEvent(
                event_id="f1",
                source=EvidenceSource.FIU_ALERT,
                region="RU",
                currency="RUB",
            )
        ],
        licensed_events=[
            LicensedPlatformEvent(
                event_id="l1",
                platform_name="KZ_Local",
                region="KZ",
                direction="deposit",
                chain=Chain.TRON,
                address="TKZ",
            )
        ],
        control_purchases=[
            ControlPurchaseEvent(
                event_id="c1",
                operator_ref="u1",
                region="RU",
                channel="p2p_rub",
                chain=Chain.TRON,
                target_address="TRU",
            )
        ],
    )

    assert weights["RU"] > weights["KZ"]

    result = attributor.attribute_address(
        address="TRU",
        chain=Chain.TRON,
        region_weights=weights,
        cluster=CryptoCluster(
            cluster_id="tron_test",
            entity_kind=EntityKind.OTC,
            confidence=0.55,
            member_addresses=["TRU"],
            evidence_sources=[EvidenceSource.CONTROL_PURCHASE],
        ),
        corridor_regions=["RU", "KZ", "TR"],
    )

    assert result.primary_region == "RU"
    assert result.confidence >= 0.55
    assert any("domestic:" in e or "corridor:" in e for e in result.evidence)
    assert not any("chainalysis" in e.lower() for e in result.evidence)


def test_all_cis_corridors_are_valid():
    for corridor in CIS_CORRIDORS:
        assert len(corridor) >= 2
        assert all(len(c) == 2 for c in corridor)
