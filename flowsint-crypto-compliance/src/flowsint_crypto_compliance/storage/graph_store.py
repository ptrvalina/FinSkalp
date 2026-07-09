"""
Unified evidence graph storage — Neo4j primary, in-memory fallback.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from flowsint_crypto_compliance.osint_core.evidence_graph import EvidenceGraph


@dataclass
class GraphPersistResult:
    backend: str
    persisted: bool
    case_ref: str
    nodes: int = 0
    edges: int = 0
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "persisted": self.persisted,
            "case_ref": self.case_ref,
            "nodes": self.nodes,
            "edges": self.edges,
            "reason": self.reason,
        }


class EvidenceGraphStore:
    def __init__(self, *, backend: str | None = None) -> None:
        self._backend = (backend or os.getenv("FINSKALP_GRAPH_BACKEND", "auto")).lower()

    def persist(
        self,
        graph: EvidenceGraph,
        *,
        case_ref: str,
        investigation_id: str | None = None,
    ) -> GraphPersistResult:
        if self._use_neo4j():
            from flowsint_crypto_compliance.storage.neo4j_exporter import (
                EvidenceGraphNeo4jExporter,
            )

            out = EvidenceGraphNeo4jExporter().export(
                graph, case_ref=case_ref, investigation_id=investigation_id
            )
            return GraphPersistResult(
                backend="neo4j",
                persisted=bool(out.get("exported")),
                case_ref=case_ref,
                nodes=int(out.get("nodes", 0)),
                edges=int(out.get("edges", 0)),
                reason=out.get("reason"),
            )
        return GraphPersistResult(
            backend="memory",
            persisted=True,
            case_ref=case_ref,
            nodes=len(graph.nodes),
            edges=len(graph.edges),
        )

    def load(self, case_ref: str) -> dict[str, Any]:
        if self._use_neo4j():
            from flowsint_crypto_compliance.storage.neo4j_exporter import (
                EvidenceGraphNeo4jExporter,
            )

            payload = EvidenceGraphNeo4jExporter().fetch_graph_payload(case_ref)
            payload["backend"] = "neo4j"
            return payload
        return {"nodes": [], "edges": [], "backend": "memory"}

    def status(self) -> dict[str, Any]:
        neo4j = self._neo4j_available()
        return {
            "configured_backend": self._backend,
            "active_backend": "neo4j" if neo4j and self._use_neo4j() else "memory",
            "neo4j_available": neo4j,
        }

    def _use_neo4j(self) -> bool:
        if self._backend == "memory":
            return False
        if self._backend == "neo4j":
            return self._neo4j_available()
        return self._neo4j_available()

    @staticmethod
    def _neo4j_available() -> bool:
        try:
            from flowsint_crypto_compliance.storage.neo4j_exporter import _get_connection

            return _get_connection() is not None
        except Exception:
            return False
