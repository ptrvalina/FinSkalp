from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from flowsint_types.fiat_crypto import EvidenceSource


class NodeKind(str, Enum):
    BANK_FEED = "bank_regulator_feed"
    FIAT_EVENT = "fiat_event"
    WALLET = "wallet"
    CLUSTER = "cluster"
    REGISTRY_LABEL = "registry_label"
    BRIDGE = "bridge"
    SUBJECT = "subject"
    PLATFORM = "platform"
    CONTROL_PURCHASE = "control_purchase"
    OSINT_MENTION = "osint_mention"


@dataclass
class EvidenceNode:
    node_id: str
    kind: NodeKind
    primary_key: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: EvidenceSource | None = None
    region: str | None = None
    confidence: float = 0.5


@dataclass
class EvidenceEdge:
    edge_id: str
    from_id: str
    to_id: str
    rel_type: str
    strength: float = 0.5
    evidence: list[str] = field(default_factory=list)


class EvidenceGraph:
    """
    In-memory evidence graph for multi-source OSINT fusion.

    All bank, registry, blockchain and regulator signals link here before merge.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, EvidenceNode] = {}
        self._edges: dict[str, EvidenceEdge] = {}
        self._index: dict[tuple[NodeKind, str], str] = {}

    @property
    def nodes(self) -> list[EvidenceNode]:
        return list(self._nodes.values())

    @property
    def edges(self) -> list[EvidenceEdge]:
        return list(self._edges.values())

    def upsert_node(
        self,
        *,
        kind: NodeKind,
        primary_key: str,
        payload: dict[str, Any] | None = None,
        source: EvidenceSource | None = None,
        region: str | None = None,
        confidence: float = 0.5,
    ) -> EvidenceNode:
        idx_key = (kind, primary_key)
        if idx_key in self._index:
            node_id = self._index[idx_key]
            node = self._nodes[node_id]
            if payload:
                node.payload.update(payload)
            node.confidence = max(node.confidence, confidence)
            return node

        node_id = f"{kind.value}:{primary_key}"
        node = EvidenceNode(
            node_id=node_id,
            kind=kind,
            primary_key=primary_key,
            payload=payload or {},
            source=source,
            region=region,
            confidence=confidence,
        )
        self._nodes[node_id] = node
        self._index[idx_key] = node_id
        return node

    def link(
        self,
        from_node: EvidenceNode,
        to_node: EvidenceNode,
        rel_type: str,
        *,
        strength: float = 0.5,
        evidence: list[str] | None = None,
    ) -> EvidenceEdge:
        edge_id = f"{from_node.node_id}--{rel_type}-->{to_node.node_id}"
        edge = EvidenceEdge(
            edge_id=edge_id,
            from_id=from_node.node_id,
            to_id=to_node.node_id,
            rel_type=rel_type,
            strength=strength,
            evidence=evidence or [],
        )
        self._edges[edge_id] = edge
        return edge

    def neighbors(self, node_id: str, rel_type: str | None = None) -> list[EvidenceEdge]:
        out = [e for e in self._edges.values() if e.from_id == node_id]
        if rel_type:
            out = [e for e in out if e.rel_type == rel_type]
        return out

    def find_node(self, kind: NodeKind, primary_key: str) -> EvidenceNode | None:
        node_id = self._index.get((kind, primary_key))
        return self._nodes.get(node_id) if node_id else None

    def get_node(self, node_id: str) -> EvidenceNode | None:
        return self._nodes.get(node_id)

    def wallet_nodes(self) -> list[EvidenceNode]:
        return [n for n in self._nodes.values() if n.kind == NodeKind.WALLET]

    def bank_to_wallet_paths(self) -> list[tuple[EvidenceNode, list[EvidenceEdge], EvidenceNode]]:
        """All bank feed → wallet linkage paths (direct or via subject/platform)."""
        paths: list[tuple[EvidenceNode, list[EvidenceEdge], EvidenceNode]] = []
        bank_nodes = [n for n in self._nodes.values() if n.kind == NodeKind.BANK_FEED]

        for bank in bank_nodes:
            for edge in self.neighbors(bank.node_id):
                target = self._nodes.get(edge.to_id)
                if not target:
                    continue
                if target.kind == NodeKind.WALLET:
                    paths.append((bank, [edge], target))
                elif target.kind in (NodeKind.SUBJECT, NodeKind.PLATFORM, NodeKind.FIAT_EVENT):
                    for edge2 in self.neighbors(target.node_id):
                        wallet = self._nodes.get(edge2.to_id)
                        if wallet and wallet.kind == NodeKind.WALLET:
                            paths.append((bank, [edge, edge2], wallet))
        return paths

    def new_subject_id(self) -> str:
        return str(uuid4())
