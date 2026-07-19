"""Evidence bridge projects sanctions / scam / exchange ownership onto wallets."""

from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.evidence_bridge import (
    build_scalpel_evidence_graph,
    serialize_evidence_graph,
)
from flowsint_crypto_compliance.osint_core.scalpel.engine import ScalpelResult
from flowsint_types.fiat_crypto import Chain


def test_bridge_marks_sanctioned_and_scam_transfers(monkeypatch):
    monkeypatch.setattr(
        "flowsint_crypto_compliance.osint_core.scalpel.evidence_bridge.ensure_local_attribution_seeds",
        lambda store: 0,
        raising=False,
    )

    seed = "TSeedWalletAddressForUnitTest00000001"
    sanc = "TSanctionedCounterparty0000000000001"
    scam = "TScamCounterpartyAddress0000000000001"
    result = ScalpelResult(
        address=seed,
        chain=Chain.TRON,
        mentions=[
            OpenMentionHit(
                source_type="registry",
                source_name="ofac",
                title_ru="OFAC SDN",
                excerpt_ru="hit",
                url=None,
                risk_tag="sanctions_screening",
                confidence=0.95,
                address=sanc,
                chain="tron",
            ),
            OpenMentionHit(
                source_type="web",
                source_name="Chainabuse",
                title_ru="Scam",
                excerpt_ru="hit",
                url=None,
                risk_tag="scam_report",
                confidence=0.8,
                address=scam,
                chain="tron",
            ),
        ],
        extracted_entities={
            "by_collector": {
                "onchain_explorer": {
                    "counterparties": [sanc, scam],
                    "transfers": [
                        {"from": seed, "to": sanc, "asset": "USDT"},
                        {"from": seed, "to": scam, "asset": "TRX"},
                    ],
                }
            }
        },
        proposed_labels=[],
    )

    graph = build_scalpel_evidence_graph(result)
    payload = serialize_evidence_graph(graph)
    by_addr = {
        n.get("address"): n
        for n in payload["nodes"]
        if n.get("kind") == "wallet" and n.get("address")
    }
    assert by_addr[sanc]["sanctioned"] is True
    assert by_addr[scam]["scam"] is True
    rels = {e["rel_type"] for e in payload["edges"]}
    assert "TRANSFER_OUT_SANCTIONED" in rels
    assert "TRANSFER_OUT_SCAM" in rels
    assert "SANCTIONED_HIT" in rels
    assert "SCAM_HIT" in rels
