from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph, NodeKind
from flowsint_crypto_compliance.osint_core.link_scorer import LinkScorer
from flowsint_types.fiat_crypto import BankRegulatorFeed, Chain, LicensedPlatformEvent


def test_link_scorer_direct_crypto_link_scores_high():
    graph = EvidenceGraph()
    bank = graph.upsert_node(
        kind=NodeKind.BANK_FEED,
        primary_key="feed-1",
        payload={"amount": 100_000, "region": "RU"},
    )
    wallet = graph.upsert_node(
        kind=NodeKind.WALLET,
        primary_key="tron:TRU_WALLET",
        payload={"amount": 100_000},
    )
    edge = graph.link(bank, wallet, "DIRECT_CRYPTO_LINK", strength=0.9)

    score = LinkScorer().score_path(bank, [edge], wallet)

    assert score.score >= 0.45
    assert "bank_direct_address" in score.signals


def test_link_scorer_bank_platform_amount_match():
    feed = BankRegulatorFeed(
        feed_id="b-1",
        bank_name="Sber",
        region="RU",
        currency="RUB",
        amount=98_000,
        linked_crypto_address="TRU_WALLET",
        linked_chain=Chain.TRON,
    )
    platform = LicensedPlatformEvent(
        event_id="v-1",
        platform_name="LocalVASP",
        region="RU",
        direction="deposit",
        chain=Chain.TRON,
        address="TRU_WALLET",
        amount_fiat=100_000,
        currency="RUB",
    )

    score = LinkScorer().score_bank_platform_wallet(feed, platform)

    assert score.score >= 0.7
    assert "region_match" in score.signals
    assert "address_exact_match" in score.signals


def test_link_scorer_inferred_bank_crypto_uses_edge_strength():
    graph = EvidenceGraph()
    bank = graph.upsert_node(
        kind=NodeKind.BANK_FEED,
        primary_key="feed-2",
        payload={"amount": 50_000},
    )
    wallet = graph.upsert_node(
        kind=NodeKind.WALLET,
        primary_key="tron:TRU_HUB",
        payload={},
    )
    edge = graph.link(
        bank,
        wallet,
        "INFERRED_BANK_CRYPTO",
        strength=0.75,
        evidence=["amount_correlation"],
    )

    score = LinkScorer().score_path(bank, [edge], wallet)

    assert score.score >= 0.4
    assert "amount_correlation" in score.signals
