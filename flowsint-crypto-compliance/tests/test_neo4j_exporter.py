from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph, NodeKind
from flowsint_crypto_compliance.services.compliance_service import _serialize_evidence_graph
from flowsint_crypto_compliance.storage.neo4j_exporter import EvidenceGraphNeo4jExporter


def test_serialize_evidence_graph():
    graph = EvidenceGraph()
    wallet = graph.upsert_node(kind=NodeKind.WALLET, primary_key="tron:TRU1", confidence=0.8)
    bank = graph.upsert_node(kind=NodeKind.BANK_FEED, primary_key="feed-1")
    graph.link(bank, wallet, "DIRECT_CRYPTO_LINK", strength=0.9)

    payload = _serialize_evidence_graph(graph)

    assert len(payload["nodes"]) == 2
    assert len(payload["edges"]) == 1
    assert payload["edges"][0]["rel_type"] == "DIRECT_CRYPTO_LINK"


def test_neo4j_exporter_graceful_without_connection():
    graph = EvidenceGraph()
    graph.upsert_node(kind=NodeKind.WALLET, primary_key="tron:TRU1")
    result = EvidenceGraphNeo4jExporter().export(graph, case_ref="CASE-TEST")
    assert result["exported"] is False
    assert result["reason"] == "neo4j_unavailable"
