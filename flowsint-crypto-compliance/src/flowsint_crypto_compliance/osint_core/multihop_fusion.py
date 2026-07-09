"""
Multi-hop Fusion Engine — рекурсивный обход контрагентов (до 3 хопов).

Hop 0: on-chain transfers → hop 1+: sanctions + abuse screening per counterparty.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from typing import Any

from flowsint_crypto_compliance.attribution.entity_label_store import get_entity_label_store
from flowsint_crypto_compliance.infrastructure.distributed_lock import DistributedLock, lock_key
from flowsint_crypto_compliance.osint_core.live_collectors import (
    collect_bitcoinabuse,
    collect_bsc_chain,
    collect_btc_chain,
    collect_eth_chain,
    collect_polygon_chain,
    collect_solana_chain,
    collect_sanctions,
    collect_tron_trc20_transfers,
)


@dataclass
class FusionGraph:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    risk_annotations: list[dict[str, Any]] = field(default_factory=list)
    corridor_flagged: bool = False
    max_hop_reached: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "risk_annotations": self.risk_annotations,
            "corridor_flagged": self.corridor_flagged,
            "max_hop_reached": self.max_hop_reached,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }


class MultiHopFusionEngine:
    def __init__(
        self,
        *,
        max_hops: int | None = None,
        max_concurrency: int | None = None,
    ) -> None:
        self._max_hops = max_hops or int(os.getenv("FINSKALP_MAX_HOPS", "3"))
        self._sem = asyncio.Semaphore(max_concurrency or int(os.getenv("FINSKALP_FUSION_CONCURRENCY", "10")))
        self._max_counterparties = int(os.getenv("FINSKALP_FUSION_MAX_COUNTERPARTIES", "12"))
        self._fusion_tx_limit = int(os.getenv("FINSKALP_FUSION_TX_LIMIT", "80"))

    async def explore(self, address: str, chain: str) -> FusionGraph:
        resource = lock_key("multihop_fusion", chain, address)
        lock = DistributedLock(ttl_sec=int(os.getenv("FINSKALP_FUSION_LOCK_TTL_SEC", "180")))
        with lock.acquire(resource) as acquired:
            if not acquired:
                graph = FusionGraph()
                graph.risk_annotations.append(
                    {
                        "type": "lock_timeout",
                        "reason_ru": "Обход графа уже выполняется для этого адреса",
                        "addresses": [address],
                    }
                )
                return graph
            return await self._explore_locked(address, chain)

    async def _explore_locked(self, address: str, chain: str) -> FusionGraph:
        graph = FusionGraph()
        visited: set[str] = set()
        illicit: set[str] = set()
        root_id = _node_id(chain, address)
        self._upsert_node(graph, root_id, address, chain, hop=0, role="root")

        await self._expand(
            graph,
            address=address,
            chain=chain,
            hop=0,
            visited=visited,
            illicit=illicit,
            parent_id=root_id,
        )
        graph.max_hop_reached = max((n.get("hop", 0) for n in graph.nodes), default=0)
        if illicit:
            graph.corridor_flagged = True
            graph.risk_annotations.append(
                {
                    "type": "corridor_flagged",
                    "reason_ru": f"Обнаружены illicit-узлы: {len(illicit)}",
                    "addresses": sorted(illicit)[:20],
                }
            )
        return graph

    async def _expand(
        self,
        graph: FusionGraph,
        *,
        address: str,
        chain: str,
        hop: int,
        visited: set[str],
        illicit: set[str],
        parent_id: str,
    ) -> None:
        key = f"{chain}:{address}"
        if key in visited:
            return
        visited.add(key)

        async with self._sem:
            try:
                transfers, counterparties = await self._fetch_transfers(address, chain)
            except Exception as exc:
                self._upsert_node(
                    graph,
                    _node_id(chain, address),
                    address,
                    chain,
                    hop=hop,
                    role="unchecked",
                    label_note=f"не проверен ({exc.__class__.__name__})",
                )
                return

        for tr in transfers:
            frm, to = tr.get("from"), tr.get("to")
            if not frm or not to:
                continue
            for cp_addr, direction in ((frm, "in"), (to, "out")):
                cp_chain = chain
                cp_id = _node_id(cp_chain, cp_addr)
                cp_hop = hop + 1 if cp_addr != address else hop
                if cp_addr != address:
                    self._upsert_node(graph, cp_id, cp_addr, cp_chain, hop=cp_hop, role="counterparty")
                self._add_edge(
                    graph,
                    _node_id(chain, frm),
                    _node_id(chain, to),
                    tr,
                )

        if hop >= self._max_hops:
            return

        screening_tasks = []
        cp_list: list[tuple[str, str]] = []
        for cp in counterparties[: self._max_counterparties]:
            if f"{chain}:{cp}" in visited:
                continue
            cp_list.append((cp, chain))
            screening_tasks.append(self._screen_address(cp, chain))

        if not screening_tasks:
            return

        results = await asyncio.gather(*screening_tasks, return_exceptions=True)
        for (cp, cp_chain), res in zip(cp_list, results):
            cp_id = _node_id(cp_chain, cp)
            self._upsert_node(graph, cp_id, cp, cp_chain, hop=hop + 1, role="counterparty")
            if isinstance(res, Exception):
                continue
            store_lbl = get_entity_label_store().lookup(cp_chain, cp)
            if store_lbl:
                graph.nodes = [
                    {**n, "label": store_lbl.label, "risk_score": store_lbl.risk_score, "category": store_lbl.category}
                    if n.get("id") == cp_id
                    else n
                    for n in graph.nodes
                ]
            if store_lbl and store_lbl.sanctioned:
                illicit.add(cp)
                graph.risk_annotations.append(
                    {
                        "type": "illicit_hit",
                        "address": cp,
                        "chain": cp_chain,
                        "hop": hop + 1,
                        "sources": [store_lbl.source],
                    }
                )
                continue
            if res.get("flagged") and res.get("sanctioned_confirmed"):
                illicit.add(cp)
                graph.risk_annotations.append(
                    {
                        "type": "illicit_hit",
                        "address": cp,
                        "chain": cp_chain,
                        "hop": hop + 1,
                        "sources": res.get("sources", []),
                    }
                )
                continue
            await self._expand(
                graph,
                address=cp,
                chain=cp_chain,
                hop=hop + 1,
                visited=visited,
                illicit=illicit,
                parent_id=cp_id,
            )

    async def _fetch_transfers(self, address: str, chain: str) -> tuple[list[dict], list[str]]:
        if chain == "tron":
            data = await collect_tron_trc20_transfers(
                address, max_transfers=self._fusion_tx_limit
            )
            return data.get("transfers") or [], data.get("counterparties") or []
        if chain == "btc":
            data = await collect_btc_chain(address)
            return data.get("transfers") or [], data.get("counterparties") or []
        if chain == "bsc":
            data = await collect_bsc_chain(address)
            return data.get("transfers") or [], data.get("counterparties") or []
        if chain == "eth":
            data = await collect_eth_chain(address)
            return data.get("transfers") or [], data.get("counterparties") or []
        if chain == "polygon":
            data = await collect_polygon_chain(address)
            return data.get("transfers") or [], data.get("counterparties") or []
        if chain == "solana":
            data = await collect_solana_chain(address)
            return data.get("transfers") or [], data.get("counterparties") or []
        return [], []

    async def _screen_address(self, address: str, chain: str) -> dict[str, Any]:
        store_lbl = get_entity_label_store().lookup(chain, address)
        if store_lbl and store_lbl.sanctioned:
            return {
                "flagged": True,
                "sanctioned_confirmed": True,
                "sources": [store_lbl.source],
            }
        async with self._sem:
            sanctions = await collect_sanctions(address)
            abuse: dict[str, Any] = {"flagged": False}
            if chain == "btc":
                abuse = await collect_bitcoinabuse(address)
        sources: list[str] = []
        sanctioned_confirmed = bool(store_lbl and store_lbl.sanctioned)
        if sanctions.get("flagged"):
            sources.append("opensanctions")
            sanctioned_confirmed = True
        if abuse.get("flagged"):
            sources.append("bitcoinabuse")
            sanctioned_confirmed = True
        return {
            "flagged": sanctioned_confirmed,
            "sanctioned_confirmed": sanctioned_confirmed,
            "sources": sources,
            "sanctions": sanctions,
            "abuse": abuse,
        }

    @staticmethod
    def _upsert_node(
        graph: FusionGraph,
        node_id: str,
        address: str,
        chain: str,
        *,
        hop: int,
        role: str,
        label_note: str | None = None,
    ) -> None:
        existing = next((n for n in graph.nodes if n["id"] == node_id), None)
        if existing:
            existing["hop"] = min(existing.get("hop", hop), hop)
            if label_note:
                existing["label"] = label_note
                existing["role"] = role
            return
        store_lbl = get_entity_label_store().lookup(chain, address)
        base_risk = float(store_lbl.risk_score) if store_lbl else 15.0
        base_cat = (store_lbl.category if store_lbl else "eoa").lower()
        base_label = (
            store_lbl.label
            if store_lbl
            else (label_note or (f"{address[:8]}…{address[-4:]}" if len(address) > 14 else address))
        )
        node_data: dict[str, Any] = {
            "id": node_id,
            "address": address,
            "chain": chain,
            "hop": hop,
            "role": role,
            "label": base_label,
            "risk_score": base_risk,
            "category": base_cat,
        }
        if store_lbl:
            node_data["attribution_source"] = store_lbl.source
            node_data["tier"] = store_lbl.tier
            node_data["sanctioned"] = store_lbl.sanctioned
        graph.nodes.append(node_data)

    @staticmethod
    def _add_edge(graph: FusionGraph, from_id: str, to_id: str, transfer: dict[str, Any]) -> None:
        edge_id = f"{from_id}->{to_id}:{transfer.get('tx_hash', uuid.uuid4().hex[:8])}"
        if any(e["id"] == edge_id for e in graph.edges):
            return
        graph.edges.append(
            {
                "id": edge_id,
                "from": from_id,
                "to": to_id,
                "amount": transfer.get("amount"),
                "timestamp": transfer.get("timestamp"),
                "tx_hash": transfer.get("tx_hash"),
                "asset": transfer.get("asset"),
                "rel_type": "SENT_TO",
            }
        )


def _node_id(chain: str, address: str) -> str:
    return f"{chain}:{address}"


def is_live_address(address: str, chain: str) -> bool:
    """Real on-chain address (not demo slug like TRU_HUB_MSK)."""
    if address.startswith("TRU_") or address.startswith("DEMO_"):
        return False
    if chain == "tron":
        return address.startswith("T") and len(address) >= 30
    if chain == "btc":
        return address.startswith(("1", "3", "bc1"))
    if chain == "eth" or chain == "bsc" or chain == "polygon":
        return address.startswith("0x") and len(address) >= 42
    return False
