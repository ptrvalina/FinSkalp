from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph, EvidenceNode, NodeKind

_NEO4J_LABEL: dict[NodeKind, str] = {
    NodeKind.BANK_FEED: "ComplianceBankFeed",
    NodeKind.FIAT_EVENT: "ComplianceFiatEvent",
    NodeKind.WALLET: "ComplianceWallet",
    NodeKind.CLUSTER: "ComplianceCluster",
    NodeKind.REGISTRY_LABEL: "ComplianceRegistryLabel",
    NodeKind.BRIDGE: "ComplianceBridge",
    NodeKind.SUBJECT: "ComplianceSubject",
    NodeKind.PLATFORM: "CompliancePlatform",
    NodeKind.CONTROL_PURCHASE: "ComplianceControlPurchase",
    NodeKind.OSINT_MENTION: "ComplianceOsintMention",
}


class EvidenceGraphNeo4jExporter:
    """Export in-memory evidence graph into Neo4j for Flowsint UI pivots."""

    def export(
        self,
        graph: EvidenceGraph,
        *,
        case_ref: str,
        investigation_id: str | None = None,
    ) -> dict[str, Any]:
        connection = _get_connection()
        if connection is None:
            return {
                "exported": False,
                "reason": "neo4j_unavailable",
                "nodes": len(graph.nodes),
                "edges": len(graph.edges),
            }

        try:
            return self._write_graph(connection, graph, case_ref=case_ref, investigation_id=investigation_id)
        except Exception:
            return {
                "exported": False,
                "reason": "neo4j_unavailable",
                "nodes": len(graph.nodes),
                "edges": len(graph.edges),
            }

    def _write_graph(
        self,
        connection,
        graph: EvidenceGraph,
        *,
        case_ref: str,
        investigation_id: str | None,
    ) -> dict[str, Any]:
        nodes_written = 0
        edges_written = 0

        connection.query(
            """
            MERGE (c:ComplianceCase {case_ref: $case_ref})
            SET c.investigation_id = $investigation_id,
                c.updated_at = datetime()
            """,
            {
                "case_ref": case_ref,
                "investigation_id": investigation_id,
            },
        )

        for node in graph.nodes:
            label = _NEO4J_LABEL.get(node.kind, "ComplianceNode")
            connection.query(
                f"""
                MATCH (c:ComplianceCase {{case_ref: $case_ref}})
                MERGE (n:{label} {{node_id: $node_id, case_ref: $case_ref}})
                SET n.kind = $kind,
                    n.primary_key = $primary_key,
                    n.payload = $payload,
                    n.region = $region,
                    n.confidence = $confidence,
                    n.source = $source
                MERGE (c)-[:HAS_EVIDENCE]->(n)
                """,
                _node_params(node, case_ref),
            )
            nodes_written += 1

        for edge in graph.edges:
            connection.query(
                """
                MATCH (a {node_id: $from_id, case_ref: $case_ref})
                MATCH (b {node_id: $to_id, case_ref: $case_ref})
                MERGE (a)-[r:COMPLIANCE_LINK {rel_type: $rel_type, case_ref: $case_ref}]->(b)
                SET r.strength = $strength,
                    r.evidence = $evidence
                """,
                {
                    "case_ref": case_ref,
                    "from_id": edge.from_id,
                    "to_id": edge.to_id,
                    "rel_type": edge.rel_type,
                    "strength": edge.strength,
                    "evidence": edge.evidence,
                },
            )
            edges_written += 1

        return {
            "exported": True,
            "case_ref": case_ref,
            "nodes": nodes_written,
            "edges": edges_written,
        }

    def fetch_graph_payload(self, case_ref: str) -> dict[str, Any]:
        """Read back compliance graph for UI (nodes + edges)."""
        connection = _get_connection()
        if connection is None:
            return {"nodes": [], "edges": []}

        nodes = connection.query(
            """
            MATCH (c:ComplianceCase {case_ref: $case_ref})-[:HAS_EVIDENCE]->(n)
            RETURN n.node_id AS id, n.kind AS kind, n.primary_key AS label,
                   n.confidence AS confidence, n.region AS region
            """,
            {"case_ref": case_ref},
        )
        edges = connection.query(
            """
            MATCH (a {case_ref: $case_ref})-[r:COMPLIANCE_LINK {case_ref: $case_ref}]->(b)
            RETURN a.node_id AS source, b.node_id AS target, r.rel_type AS rel_type,
                   r.strength AS strength
            """,
            {"case_ref": case_ref},
        )
        return {"nodes": nodes, "edges": edges}


def _node_params(node: EvidenceNode, case_ref: str) -> dict[str, Any]:
    return {
        "case_ref": case_ref,
        "node_id": node.node_id,
        "kind": node.kind.value,
        "primary_key": node.primary_key,
        "payload": node.payload,
        "region": node.region,
        "confidence": node.confidence,
        "source": node.source.value if node.source else None,
    }


def _get_connection():
    try:
        from flowsint_core.core.graph import connection as neo4j_mod

        return getattr(neo4j_mod, "neo4j_connection", None)
    except Exception:
        return None
