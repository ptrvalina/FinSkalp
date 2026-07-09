"""
Neo4j Wallet Graph — thin facade over Neo4jUnifiedProjection (RFC-0002 M2, TD-S2).

Legacy (:Wallet)-[:SENT_TO]->(:Wallet) Cypher queries are retained for read compat.
New writes prefer canonical Finskalp* labels via Neo4jUnifiedProjection.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import Entity, EntityType
from flowsint_crypto_compliance.platform.v2.neo4j_projection import Neo4jUnifiedProjection


class WalletNeo4jStore:
    def __init__(self) -> None:
        self._conn = _connection()
        self._projection = Neo4jUnifiedProjection()

    @property
    def available(self) -> bool:
        return self._conn is not None

    def persist_fusion_graph(self, graph: dict[str, Any], *, case_ref: str) -> dict[str, Any]:
        if not self._conn:
            return {"persisted": False, "reason": "neo4j_unavailable"}
        nodes = graph.get("nodes") or []
        edges = graph.get("edges") or []
        annotations = graph.get("risk_annotations") or []

        tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
        tenant_id = uuid.UUID(tenant_raw)
        unified: list[dict[str, Any]] = []

        self._conn.query(
            """
            MERGE (c:FinSkalpCase {case_ref: $case_ref})
            SET c.updated_at = datetime()
            """,
            {"case_ref": case_ref},
        )

        for node in nodes:
            chain = str(node.get("chain") or "unknown")
            address = str(node.get("address") or node.get("id") or "")
            canonical_key = f"{chain}:{address}" if ":" not in address else address
            ent = Entity(
                tenant_id=tenant_id,
                entity_type=EntityType.WALLET,
                canonical_key=canonical_key,
                display_name=str(node.get("label") or address),
            )
            unified.append(self._projection.project_entity(ent, case_ref=case_ref))

            self._conn.query(
                """
                MATCH (c:FinSkalpCase {case_ref: $case_ref})
                MERGE (w:Wallet {id: $id, case_ref: $case_ref})
                SET w.address = $address, w.chain = $chain, w.hop = $hop,
                    w.role = $role, w.label = $label
                MERGE (c)-[:INVESTIGATES]->(w)
                """,
                {
                    "case_ref": case_ref,
                    "id": node["id"],
                    "address": node["address"],
                    "chain": node["chain"],
                    "hop": node.get("hop", 0),
                    "role": node.get("role", ""),
                    "label": node.get("label", ""),
                },
            )

        for edge in edges:
            self._conn.query(
                """
                MATCH (a:Wallet {id: $from_id, case_ref: $case_ref})
                MATCH (b:Wallet {id: $to_id, case_ref: $case_ref})
                MERGE (a)-[r:SENT_TO {tx_hash: $tx_hash, case_ref: $case_ref}]->(b)
                SET r.amount = $amount, r.timestamp = $timestamp, r.asset = $asset
                """,
                {
                    "case_ref": case_ref,
                    "from_id": edge["from"],
                    "to_id": edge["to"],
                    "tx_hash": edge.get("tx_hash") or "",
                    "amount": edge.get("amount"),
                    "timestamp": edge.get("timestamp"),
                    "asset": edge.get("asset"),
                },
            )
            from_node = next((n for n in nodes if n.get("id") == edge.get("from")), None)
            to_node = next((n for n in nodes if n.get("id") == edge.get("to")), None)
            if from_node and to_node:
                f_chain = str(from_node.get("chain") or "unknown")
                t_chain = str(to_node.get("chain") or "unknown")
                f_addr = str(from_node.get("address") or from_node.get("id") or "")
                t_addr = str(to_node.get("address") or to_node.get("id") or "")
                self._projection.project_relation(
                    from_key=f"{f_chain}:{f_addr}",
                    to_key=f"{t_chain}:{t_addr}",
                    tenant_id=tenant_raw,
                    relation_type="SENT_TO",
                    case_ref=case_ref,
                )

        for ann in annotations:
            if ann.get("type") != "illicit_hit":
                continue
            addr = ann.get("address", "")
            chain = ann.get("chain", "")
            nid = f"{chain}:{addr}"
            self._conn.query(
                """
                MATCH (w:Wallet {id: $id, case_ref: $case_ref})
                MERGE (s:SanctionEntry {id: $sid, case_ref: $case_ref})
                SET s.sources = $sources, s.hop = $hop
                MERGE (w)-[:FLAGGED_BY]->(s)
                """,
                {
                    "case_ref": case_ref,
                    "id": nid,
                    "sid": f"flag:{nid}",
                    "sources": ann.get("sources") or [],
                    "hop": ann.get("hop", 0),
                },
            )

        return {
            "persisted": True,
            "case_ref": case_ref,
            "nodes": len(nodes),
            "edges": len(edges),
            "unified_projection": unified,
        }

    def shortest_path(self, case_ref: str, from_id: str, to_id: str) -> dict[str, Any]:
        if not self._conn:
            return {"path": [], "reason": "neo4j_unavailable"}
        rows = self._conn.query(
            """
            MATCH (a:Wallet {id: $from_id, case_ref: $case_ref}),
                  (b:Wallet {id: $to_id, case_ref: $case_ref}),
                  p = shortestPath((a)-[:SENT_TO*..8]-(b))
            RETURN [n IN nodes(p) | n.id] AS path,
                   length(p) AS hops
            LIMIT 1
            """,
            {"case_ref": case_ref, "from_id": from_id, "to_id": to_id},
        )
        return rows[0] if rows else {"path": [], "hops": 0}

    def n_hop_from_illicit(self, case_ref: str, max_hops: int = 3) -> list[dict[str, Any]]:
        if not self._conn:
            return []
        return self._conn.query(
            """
            MATCH (s:SanctionEntry {case_ref: $case_ref})<-[:FLAGGED_BY]-(illicit:Wallet)
            MATCH (w:Wallet {case_ref: $case_ref})
            WHERE w <> illicit
            MATCH p = shortestPath((illicit)-[:SENT_TO*1..$max_hops]-(w))
            RETURN DISTINCT w.id AS wallet_id, w.address AS address, length(p) AS distance
            LIMIT 100
            """,
            {"case_ref": case_ref, "max_hops": max_hops},
        )

    def detect_cycles(self, case_ref: str, min_length: int = 3) -> list[dict[str, Any]]:
        """Cycle detection — признак mixing/layering."""
        if not self._conn:
            return []
        return self._conn.query(
            """
            MATCH (w:Wallet {case_ref: $case_ref})
            MATCH p = (w)-[:SENT_TO*3..6]->(w)
            RETURN [n IN nodes(p) | n.id] AS cycle, length(p) AS cycle_length
            LIMIT 20
            """,
            {"case_ref": case_ref},
        )

    def link_vasp(self, case_ref: str, wallet_id: str, vasp_name: str, *, license_id: str = "") -> None:
        if not self._conn:
            return
        self._conn.query(
            """
            MATCH (w:Wallet {id: $wallet_id, case_ref: $case_ref})
            MERGE (v:VASP {name: $name, case_ref: $case_ref})
            SET v.license_id = $license_id
            MERGE (w)-[:BELONGS_TO]->(v)
            """,
            {
                "case_ref": case_ref,
                "wallet_id": wallet_id,
                "name": vasp_name,
                "license_id": license_id,
            },
        )


def _connection():
    try:
        from flowsint_crypto_compliance.storage.neo4j_exporter import _get_connection

        return _get_connection()
    except Exception:
        return None
