from unittest.mock import patch

import pytest

from flowsint_crypto_compliance.ingestion.enforcement_feeds import (
    EnforcementRecord,
    _extract_addresses,
    _merge_store,
    lookup_address,
)
from flowsint_crypto_compliance.ml.graphsage import graph_metrics_and_embedding
from flowsint_crypto_compliance.ml.onnx_inference import ONNXRiskScorer
from flowsint_crypto_compliance.ml.scoring_pipeline import score_risk
from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph, NodeKind
from flowsint_crypto_compliance.osint_core.open_source_collector import OpenMentionHit
from flowsint_crypto_compliance.osint_core.scalpel.evidence_bridge import (
    build_scalpel_evidence_graph,
    scalpel_case_ref,
)
from flowsint_crypto_compliance.osint_core.scalpel.engine import ScalpelResult
from flowsint_crypto_compliance.storage.graph_store import EvidenceGraphStore
from flowsint_types.fiat_crypto import Chain


def test_extract_crypto_addresses_from_text():
    text = (
        "Seized wallet 0x0000000000000000000000000000000000000001 "
        "and TUVHw4wBAwGEMRx2q4AXymX7FWLKXAqWJE"
    )
    addrs = _extract_addresses(text)
    chains = {a["chain"] for a in addrs}
    assert "eth" in chains
    assert "tron" in chains


def test_enforcement_lookup():
    rec = EnforcementRecord(
        record_id="DOJ:test1",
        source="DOJ",
        title="Crypto seizure",
        url="https://justice.gov/test",
        published_at="2026-01-01",
        excerpt="Bitcoin wallet seized",
        addresses=[{"chain": "tron", "address": "TRU_HUB_MSK"}],
    )
    merged = _merge_store([rec])
    with patch(
        "flowsint_crypto_compliance.ingestion.enforcement_feeds.load_enforcement_store",
        return_value=merged,
    ):
        hits = lookup_address("TRU_HUB_MSK", "tron")
    assert len(hits) == 1


def test_graph_store_memory_backend():
    graph = EvidenceGraph()
    graph.upsert_node(kind=NodeKind.WALLET, primary_key="tron:ADDR", confidence=0.8)
    out = EvidenceGraphStore(backend="memory").persist(graph, case_ref="CASE-1")
    assert out.persisted
    assert out.backend == "memory"
    assert out.nodes == 1


def test_scalpel_evidence_graph_builds_entities():
    result = ScalpelResult(
        address="TRU_HUB_MSK",
        chain=Chain.TRON,
        mentions=[
            OpenMentionHit(
                source_type="telegram",
                source_name="tg",
                title_ru="OTC",
                excerpt_ru="ИНН 7707083893 @otc_user",
                url=None,
                risk_tag="otc_gray",
                confidence=0.7,
                address="TRU_HUB_MSK",
                chain="tron",
            )
        ],
        extracted_entities={
            "aggregate": {"inn": ["7707083893"], "phones": [], "usernames": ["otc_user"]}
        },
    )
    g = build_scalpel_evidence_graph(result)
    assert len(g.nodes) >= 3
    assert scalpel_case_ref("TRU_HUB_MSK", Chain.TRON).startswith("SCALPEL-TRON-")


def test_graphsage_metrics():
    graph = EvidenceGraph()
    w = graph.upsert_node(kind=NodeKind.WALLET, primary_key="tron:A", confidence=0.9)
    m = graph.upsert_node(kind=NodeKind.OSINT_MENTION, primary_key="m1", confidence=0.7)
    graph.link(w, m, "OSINT_MENTION", strength=0.7)
    metrics = graph_metrics_and_embedding(graph, wallet_primary_key="tron:A")
    assert metrics["graph_degree"] >= 1.0
    assert "graphsage_embedding_0" in metrics


def test_ml_scoring_heuristic_without_onnx():
    mentions = [
        OpenMentionHit(
            source_type="web",
            source_name="Chainabuse",
            title_ru="scam",
            excerpt_ru="report",
            url=None,
            risk_tag="scam_report",
            confidence=0.8,
        )
    ]
    out = score_risk("ADDR", "tron", mentions)
    assert 0 <= out["score"] <= 100
    assert out["backend"] in ("heuristic", "onnx")


def test_train_and_onnx_inference(tmp_path):
    onnxmltools = pytest.importorskip("onnxmltools")
    assert onnxmltools
    from flowsint_crypto_compliance.ml.train_baseline import train_and_export

    model_path = tmp_path / "risk_xgb.onnx"
    train_and_export(out_path=model_path)
    assert model_path.is_file()
    scorer = ONNXRiskScorer(model_path=model_path)
    assert scorer.available
    result = scorer.score([])
    assert "score" in result
