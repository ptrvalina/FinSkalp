"""FTM adapter roundtrip tests."""

from flowsint_crypto_compliance.attribution.entity_label_store import EntityLabelStore, reset_entity_label_store
from flowsint_crypto_compliance.attribution.types import EntityLabel
from flowsint_crypto_compliance.interop.ftm_adapter import (
    entity_label_to_ftm_entity,
    export_labels_ftm_ndjson,
    ftm_entity_to_entity_label,
    import_labels_from_ftm_ndjson,
)


def _sample_label(**kwargs) -> EntityLabel:
    defaults = dict(
        address="TQn9Yz2r8p7bLSEz7K8vJ3mN4pQ2wR5tYX",
        chain="tron",
        label="TQn9Yz2r8p7bLSEz7K8vJ3mN4pQ2wR5tYX",
        category="exchange",
        confidence=0.9,
        source="finskalp",
        tier=2,
        risk_score=12.0,
        evidence="test:ftm",
    )
    defaults.update(kwargs)
    return EntityLabel(**defaults)


def test_entity_label_to_ftm_crypto_wallet():
    lbl = _sample_label()
    ftm = entity_label_to_ftm_entity(lbl)
    assert ftm["schema"] == "CryptoWallet"
    assert ftm["caption"] == lbl.address
    assert lbl.address in ftm["properties"]["cryptoWallet"]
    assert ftm["properties"]["currency"] == ["trx"]
    assert "exchange" in ftm["properties"]["topics"]
    assert ftm["datasets"] == ["finskalp"]


def test_entity_label_to_ftm_legal_entity():
    lbl = _sample_label(label="Acme OTC Desk RU", address="0x3f5ce5fbfe3e9ee397108865aa489f795bb6ff99", chain="eth")
    ftm = entity_label_to_ftm_entity(lbl)
    assert ftm["schema"] == "LegalEntity"
    assert ftm["properties"]["name"] == ["Acme OTC Desk RU"]


def test_ftm_roundtrip_via_ndjson():
    reset_entity_label_store()
    store = EntityLabelStore()
    original = _sample_label()
    ndjson = export_labels_ftm_ndjson([original])
    stats = import_labels_from_ftm_ndjson(ndjson, store)
    assert stats["loaded"] == 1
    restored = store.lookup("tron", original.address)
    assert restored is not None
    assert restored.label == original.label
    assert restored.chain == original.chain
    assert restored.category == original.category


def test_opensanctions_style_ftm_row():
    row = {
        "id": "os-abc123",
        "caption": "Sanctioned Entity",
        "datasets": ["opensanctions"],
        "properties": {
            "cryptoWallet": ["0x3f5ce5fbfe3e9ee397108865aa489f795bb6ff99"],
            "currency": ["eth"],
            "topics": ["sanction"],
        },
    }
    lbl = ftm_entity_to_entity_label(row)
    assert lbl is not None
    assert lbl.chain == "eth"
    assert lbl.sanctioned is True
    assert lbl.source == "opensanctions"


def test_fusion_ftm_bundle():
    from flowsint_crypto_compliance.interop.fusion_ftm_export import fusion_graph_to_ftm_bundle

    graph = {
        "nodes": [
            {"id": "tron:root", "address": "TRoot", "chain": "tron", "hop": 0, "label": "Root"},
            {"id": "tron:a1", "address": "TA1", "chain": "tron", "hop": 1, "label": "Counterparty"},
        ],
        "edges": [{"from": "tron:a1", "to": "tron:root", "amount": 500}],
    }
    bundle = fusion_graph_to_ftm_bundle(graph)
    assert bundle["version"] == "fusion_graph_ftm_export_v1"
    assert bundle["entity_count"] == 2
    assert bundle["statement_count"] == 1
    assert bundle["statements"][0]["schema"] == "Payment"
