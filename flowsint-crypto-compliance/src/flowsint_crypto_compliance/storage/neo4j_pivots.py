"""Neo4j pivot nodes compatible with Flowsint enricher graph UI."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph, NodeKind
from flowsint_crypto_compliance.storage.neo4j_exporter import _get_connection


class ComplianceNeo4jPivotExporter:
    """Export wallet/subject pivots for flowsint-enrichers postprocess hooks."""

    def export(self, graph: EvidenceGraph, *, case_ref: str) -> dict[str, Any]:
        connection = _get_connection()
        if connection is None:
            return {"exported": False, "reason": "neo4j_unavailable", "pivots": 0}

        try:
            return self._write_pivots(connection, graph, case_ref=case_ref)
        except Exception:
            return {"exported": False, "reason": "neo4j_unavailable", "pivots": 0}

    def _write_pivots(self, connection, graph: EvidenceGraph, *, case_ref: str) -> dict[str, Any]:
        pivots = 0
        for node in graph.nodes:
            if node.kind not in {NodeKind.WALLET, NodeKind.SUBJECT, NodeKind.BANK_FEED}:
                continue
            label = _pivot_label(node.kind)
            connection.query(
                f"""
                MERGE (c:ComplianceCase {{case_ref: $case_ref}})
                MERGE (p:{label} {{primary_key: $primary_key, case_ref: $case_ref}})
                SET p.kind = $kind,
                    p.confidence = $confidence,
                    p.region = $region,
                    p.flowsint_pivot = true
                MERGE (c)-[:COMPLIANCE_PIVOT]->(p)
                """,
                {
                    "case_ref": case_ref,
                    "primary_key": node.primary_key,
                    "kind": node.kind.value,
                    "confidence": node.confidence,
                    "region": node.region,
                },
            )
            pivots += 1

        for edge in graph.edges:
            connection.query(
                """
                MATCH (a {primary_key: $from_key, case_ref: $case_ref})
                MATCH (b {primary_key: $to_key, case_ref: $case_ref})
                MERGE (a)-[r:FLOWSINT_PIVOT {rel_type: $rel_type, case_ref: $case_ref}]->(b)
                SET r.strength = $strength
                """,
                {
                    "case_ref": case_ref,
                    "from_key": _primary_key_for_id(graph, edge.from_id),
                    "to_key": _primary_key_for_id(graph, edge.to_id),
                    "rel_type": edge.rel_type,
                    "strength": edge.strength,
                },
            )

        return {"exported": True, "case_ref": case_ref, "pivots": pivots}


def _pivot_label(kind: NodeKind) -> str:
    if kind == NodeKind.WALLET:
        return "CryptoWallet"
    if kind == NodeKind.SUBJECT:
        return "ComplianceSubject"
    return "ComplianceBankFeed"


def _primary_key_for_id(graph: EvidenceGraph, node_id: str) -> str:
    for node in graph.nodes:
        if node.node_id == node_id:
            return node.primary_key
    return node_id
