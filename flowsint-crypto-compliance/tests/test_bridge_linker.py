import pytest

from flowsint_crypto_compliance.chains.base import InMemoryChainAdapter, OnChainTransfer
from flowsint_crypto_compliance.engine.bridge_linker import BridgeLinker, BridgeTraceConfig
from flowsint_crypto_compliance.engine.clusterer import ClusterEngine
from flowsint_types.fiat_crypto import (
    Chain,
    ControlPurchaseEvent,
    EvidenceSource,
    FiatLegEvent,
    LicensedPlatformEvent,
)


def test_cluster_engine_groups_licensed_platform_addresses():
    engine = ClusterEngine()
    events = [
        LicensedPlatformEvent(
            event_id="lp1",
            platform_name="LocalExchangeIN",
            region="IN",
            direction="deposit",
            chain=Chain.TRON,
            address="TAddr1",
        ),
        LicensedPlatformEvent(
            event_id="lp2",
            platform_name="LocalExchangeIN",
            region="IN",
            direction="withdrawal",
            chain=Chain.TRON,
            address="TAddr2",
        ),
    ]
    engine.ingest_licensed_events(events)
    clusters = engine.build_clusters(min_confidence=0.2)

    assert len(clusters) == 1
    assert clusters[0].claimed_entity == "LocalExchangeIN"
    assert clusters[0].region_weights.get("IN") == 1.0


def test_control_purchase_links_to_cluster():
    engine = ClusterEngine()
    engine.ingest_control_purchases(
        [
            ControlPurchaseEvent(
                event_id="cp1",
                operator_ref="unit-7",
                region="RU",
                channel="P2P",
                chain=Chain.TRON,
                source_address="TGray1",
                target_address="TGray2",
            )
        ]
    )
    clusters = engine.build_clusters(min_confidence=0.2)
    assert any("TGray2" in (c.member_addresses or []) for c in clusters)


@pytest.mark.asyncio
async def test_bridge_linker_traces_cis_to_latam_scenario():
    """СНГ control purchase → gray hop → licensed platform in Dominican Republic."""
    transfers = [
        OnChainTransfer(
            chain=Chain.TRON,
            tx_hash="tx1",
            source="TGray1",
            target="TGray2",
            asset="USDT",
            amount=1000,
        ),
        OnChainTransfer(
            chain=Chain.TRON,
            tx_hash="tx2",
            source="TGray2",
            target="TDOExchange",
            asset="USDT",
            amount=1000,
        ),
    ]
    adapter = InMemoryChainAdapter(Chain.TRON, transfers)
    linker = BridgeLinker(
        adapters={Chain.TRON: adapter},
        config=BridgeTraceConfig(max_hops=3, min_bridge_confidence=0.3),
    )

    fiat_event = FiatLegEvent(
        event_id="fiu-001",
        source=EvidenceSource.FIU_ALERT,
        region="RU",
        currency="RUB",
        amount=85000,
        platform_id="P2P_Channel_X",
    )
    control = ControlPurchaseEvent(
        event_id="cp-russia",
        operator_ref="unit-7",
        region="RU",
        channel="P2P",
        chain=Chain.TRON,
        source_address="TGray1",
        target_address="TGray2",
    )
    licensed = LicensedPlatformEvent(
        event_id="do-dep-1",
        platform_name="DO_Local_CEX",
        region="DO",
        direction="deposit",
        chain=Chain.TRON,
        address="TDOExchange",
        asset="USDT",
    )

    context = await linker.build_context(
        fiat_events=[fiat_event],
        licensed_events=[licensed],
        control_purchases=[control],
    )
    bridges = await linker.trace_fiat_event(fiat_event, context)

    assert bridges
    best = max(bridges, key=lambda b: b.confidence)
    assert best.region_origin == "RU"
    assert best.exit_address == "TDOExchange"
    assert best.region_destination == "DO"
    assert best.confidence >= 0.5
