"""
Top-tier graph enrichments: cluster_view + direct/indirect exposure paths.

Feeds FinSkalp force-graph UI (Chainalysis/Elliptic-style drill-down).
"""

from __future__ import annotations

import hashlib
import html
from collections import defaultdict, deque
from copy import deepcopy
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring


_CHAIN_COLORS = {
    "tron": "#ef4444",
    "eth": "#6366f1",
    "btc": "#f59e0b",
    "bsc": "#eab308",
    "polygon": "#a855f7",
}

# Public bridge / DEX router contracts (open block-explorer data).
_KNOWN_BRIDGES: dict[str, dict[str, str]] = {
    "0x6b7a87899490ece95443eac7ce0b94bfe892fd8": {
        "name": "Multichain Router",
        "chain": "eth",
        "bridge_type": "multichain",
    },
    "0xdd5b5bc006a99e766e04f8edd6a778ed070b14f1": {
        "name": "cBridge (BSC)",
        "chain": "bsc",
        "bridge_type": "cbridge",
    },
    "0x10ed43c718714eb63d5aa57b78b54704e256024e": {
        "name": "PancakeSwap Router",
        "chain": "bsc",
        "bridge_type": "dex",
    },
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": {
        "name": "Uniswap V2 Router",
        "chain": "eth",
        "bridge_type": "dex",
    },
    "tkzxdv2t6kk7k1a48kqvzk1srvde9be9fe": {
        "name": "SunSwap V2 Router",
        "chain": "tron",
        "bridge_type": "dex",
    },
}

# Tron base58 is case-sensitive; index aliases for lookup.
_BRIDGE_LOOKUP: dict[str, dict[str, str]] = dict(_KNOWN_BRIDGES)
_BRIDGE_LOOKUP["TKzxdv2T6kk7k1a48KQvzk1sRvde9BE9Fe"] = _KNOWN_BRIDGES[
    "tkzxdv2t6kk7k1a48kqvzk1srvde9be9fe"
]

_CROSS_CHAIN_WINDOW_MS = 6 * 3600 * 1000


def enrich_investigation_graph(
    graph: dict[str, Any] | None,
    *,
    root_address: str | None = None,
    screening: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add address_view, cluster_view, exposure_paths for UI."""
    if not graph or not graph.get("nodes"):
        return graph or {"nodes": [], "edges": []}

    address_view = deepcopy(graph)
    root_id = _find_root_id(address_view, root_address)
    illicit = _illicit_node_ids(address_view)
    kyt = ((screening or {}).get("onchain_summary") or {}).get("kyt_exposure") or {}
    onchain = (screening or {}).get("onchain_summary") or {}

    _attach_root_portfolio(address_view, root_id=root_id, onchain=onchain)

    _annotate_edge_exposure(address_view, root_id=root_id, illicit_ids=illicit, kyt=kyt)
    _annotate_cross_chain(address_view)
    from flowsint_crypto_compliance.engine.defi_detector import annotate_defi

    annotate_defi(address_view)
    exposure_paths = _build_exposure_paths(address_view, root_id=root_id, illicit_ids=illicit)
    cluster_view = build_cluster_view(address_view, root_id=root_id)
    timeline = _build_timeline(address_view)

    out = dict(graph)
    out["address_view"] = address_view
    out["cluster_view"] = cluster_view
    out["exposure_paths"] = exposure_paths
    out["timeline"] = timeline
    out["default_view"] = "cluster"
    out["chain_colors"] = _CHAIN_COLORS
    out["illicit_node_ids"] = sorted(illicit)
    out["cross_chain_links"] = address_view.get("cross_chain_links") or []
    out["defi_hits"] = address_view.get("defi_hits") or []
    out["defi_detected"] = bool(address_view.get("defi_detected"))
    return out


def build_cluster_view(address_view: dict[str, Any], *, root_id: str | None = None) -> dict[str, Any]:
    """Collapse labeled / co-owned addresses into super-nodes."""
    nodes = address_view.get("nodes") or []
    edges = address_view.get("edges") or []
    if not nodes:
        return {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0}

    root_id = root_id or _find_root_id(address_view, None)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for n in nodes:
        if n.get("id") == root_id or n.get("hop") == 0:
            groups[root_id or n["id"]].append(n)
            continue
        if n.get("role") == "cluster" or str(n.get("id", "")).startswith("__cluster"):
            groups[str(n["id"])].append(n)
            continue
        key = _cluster_key(n)
        groups[key].append(n)

    super_nodes: dict[str, dict[str, Any]] = {}
    member_map: dict[str, str] = {}

    for gkey, members in groups.items():
        if len(members) == 1 and members[0].get("id") == root_id:
            n = members[0]
            super_nodes[n["id"]] = {**n, "node_type": "address", "member_count": 1, "members": [n["id"]]}
            member_map[n["id"]] = n["id"]
            continue
        if len(members) == 1:
            n = members[0]
            super_nodes[n["id"]] = {**n, "node_type": "address", "member_count": 1, "members": [n["id"]]}
            member_map[n["id"]] = n["id"]
            continue

        rep = max(members, key=lambda m: float(m.get("risk_score") or 0))
        vol = sum(float(m.get("volume_usd") or 0) for m in members)
        sid = f"cluster:{gkey}"
        label = rep.get("label") or rep.get("category") or "EOA cluster"
        super_nodes[sid] = {
            "id": sid,
            "node_type": "cluster",
            "label": f"{label} ({len(members)})",
            "address": rep.get("address", ""),
            "chain": rep.get("chain", "tron"),
            "hop": min(int(m.get("hop") or 1) for m in members),
            "role": "cluster",
            "risk_score": max(float(m.get("risk_score") or 0) for m in members),
            "category": rep.get("category") or "cluster",
            "member_count": len(members),
            "members": [m["id"] for m in members],
            "volume_usd": vol,
            "sanctioned": any(m.get("sanctioned") for m in members),
            "expandable": True,
        }
        for m in members:
            member_map[m["id"]] = sid

    agg_edges: dict[tuple[str, str], dict[str, Any]] = {}
    for e in edges:
        fr = member_map.get(e.get("from") or "", e.get("from"))
        to = member_map.get(e.get("to") or "", e.get("to"))
        if not fr or not to or fr == to:
            continue
        key = (fr, to)
        if key not in agg_edges:
            agg_edges[key] = {
                "id": f"{fr}->{to}",
                "from": fr,
                "to": to,
                "amount": 0.0,
                "asset": e.get("asset"),
                "exposure_type": e.get("exposure_type", "transfer"),
                "hops": e.get("hops"),
                "edge_count": 0,
            }
        agg_edges[key]["amount"] = float(agg_edges[key]["amount"] or 0) + float(e.get("amount") or 0)
        agg_edges[key]["edge_count"] += 1
        if e.get("exposure_type") == "direct":
            agg_edges[key]["exposure_type"] = "direct"

    cluster_edges = list(agg_edges.values())
    node_list = list(super_nodes.values())
    return {
        "nodes": node_list,
        "edges": cluster_edges,
        "risk_annotations": address_view.get("risk_annotations") or [],
        "corridor_flagged": address_view.get("corridor_flagged", False),
        "node_count": len(node_list),
        "edge_count": len(cluster_edges),
        "view": "cluster",
        "member_map": member_map,
    }


def _attach_root_portfolio(
    graph: dict[str, Any], *, root_id: str | None, onchain: dict[str, Any]
) -> None:
    if not root_id or not onchain:
        return
    tokens = onchain.get("tokens") or []
    balance_usd = onchain.get("balance_usd")
    for n in graph.get("nodes") or []:
        if n.get("id") == root_id or n.get("hop") == 0:
            if tokens:
                n["portfolio"] = tokens[:8]
            if balance_usd is not None:
                n["balance_usd"] = balance_usd
            break


def _cluster_key(node: dict[str, Any]) -> str:
    label = (node.get("label") or "").strip().lower()
    category = (node.get("category") or "unknown").strip().lower()
    if label and label not in ("unknown", "—", ""):
        raw = f"{category}:{label}"
    else:
        raw = f"eoa:{node.get('chain', 'tron')}:{node.get('hop', 1)}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def _find_root_id(graph: dict[str, Any], root_address: str | None) -> str:
    for n in graph.get("nodes") or []:
        if n.get("hop") == 0:
            return str(n["id"])
    if root_address:
        for n in graph.get("nodes") or []:
            if (n.get("address") or "").lower() == root_address.lower():
                return str(n["id"])
    nodes = graph.get("nodes") or []
    return str(nodes[0]["id"]) if nodes else ""


def _illicit_node_ids(graph: dict[str, Any]) -> set[str]:
    illicit: set[str] = set()
    for n in graph.get("nodes") or []:
        if n.get("sanctioned") or n.get("role") == "illicit":
            cat = str(n.get("category") or "").lower()
            if n.get("sanctioned") or cat in ("sanctions", "mixer", "scam", "illicit", "illegal_service"):
                illicit.add(str(n["id"]))
    addr_to_id = {str(n.get("address", "")).lower(): str(n["id"]) for n in graph.get("nodes") or []}
    for ann in graph.get("risk_annotations") or []:
        if ann.get("type") in ("illicit_hit", "corridor_flagged"):
            addr = str(ann.get("address") or "").lower()
            if addr in addr_to_id:
                illicit.add(addr_to_id[addr])
    return illicit


def _annotate_edge_exposure(
    graph: dict[str, Any],
    *,
    root_id: str,
    illicit_ids: set[str],
    kyt: dict[str, Any],
) -> None:
    """Mark edges direct vs indirect; attach hop counts from KYT rows."""
    kyt_by_addr: dict[str, dict[str, Any]] = {}
    for row in (kyt.get("indirect_exposure") or []) + (kyt.get("connections") or []):
        addr = str(row.get("address") or row.get("wallet_address") or "").lower()
        if addr:
            kyt_by_addr[addr] = row

    id_to_addr = {str(n["id"]): str(n.get("address") or "").lower() for n in graph.get("nodes") or []}

    for e in graph.get("edges") or []:
        fr, to = str(e.get("from")), str(e.get("to"))
        hop_dst = int(
            next((n.get("hop", 99) for n in graph.get("nodes") or [] if str(n.get("id")) == to), 99)
        )
        cp_addr = id_to_addr.get(fr if to == root_id else to, "")
        kyt_row = kyt_by_addr.get(cp_addr, {})
        behavior = str(kyt_row.get("behavior") or "").lower()
        hops = kyt_row.get("hops")

        touches_illicit = fr in illicit_ids or to in illicit_ids
        if hop_dst <= 1 and (touches_illicit or behavior == "direct"):
            e["exposure_type"] = "direct"
            e["hops"] = 1
        elif hops:
            e["exposure_type"] = "indirect"
            e["hops"] = int(hops)
        elif hop_dst > 1 or touches_illicit:
            e["exposure_type"] = "indirect"
            e["hops"] = hop_dst
        else:
            e["exposure_type"] = e.get("exposure_type") or "transfer"
            e["hops"] = hop_dst or 1


def _build_exposure_paths(
    graph: dict[str, Any],
    *,
    root_id: str,
    illicit_ids: set[str],
) -> list[dict[str, Any]]:
    if not root_id or not illicit_ids:
        return []

    adj: dict[str, list[str]] = defaultdict(list)
    for e in graph.get("edges") or []:
        fr, to = str(e.get("from")), str(e.get("to"))
        adj[fr].append(to)
        adj[to].append(fr)

    paths: list[dict[str, Any]] = []
    for target in illicit_ids:
        if target == root_id:
            continue
        path = _bfs_path(adj, root_id, target)
        if path:
            paths.append(
                {
                    "target_id": target,
                    "target_address": _addr_for_id(graph, target),
                    "hops": max(0, len(path) - 1),
                    "path": path,
                    "exposure_type": "direct" if len(path) <= 2 else "indirect",
                }
            )
    paths.sort(key=lambda p: p["hops"])
    return paths


def _bfs_path(adj: dict[str, list[str]], start: str, goal: str) -> list[str]:
    q: deque[str] = deque([start])
    prev: dict[str, str | None] = {start: None}
    while q:
        cur = q.popleft()
        if cur == goal:
            break
        for nxt in adj.get(cur, []):
            if nxt not in prev:
                prev[nxt] = cur
                q.append(nxt)
    if goal not in prev:
        return []
    path: list[str] = []
    cur: str | None = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def _addr_for_id(graph: dict[str, Any], node_id: str) -> str:
    for n in graph.get("nodes") or []:
        if str(n.get("id")) == node_id:
            return str(n.get("address") or "")
    return ""


def _norm_addr(addr: str) -> str:
    a = (addr or "").strip()
    return a.lower() if a.startswith("0x") else a


def _bridge_meta(addr: str) -> dict[str, str] | None:
    return _BRIDGE_LOOKUP.get(_norm_addr(addr)) or _BRIDGE_LOOKUP.get((addr or "").strip())


def _annotate_cross_chain(graph: dict[str, Any]) -> None:
    """Mark bridge nodes and infer cross-chain hops (heuristic, confidence-scored)."""
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    id_to_node = {str(n["id"]): n for n in nodes}
    cross_links: list[dict[str, Any]] = []

    for n in nodes:
        meta = _bridge_meta(str(n.get("address") or ""))
        if meta:
            n["role"] = "bridge"
            n["category"] = "bridge"
            n["label"] = meta["name"]
            n["bridge_type"] = meta["bridge_type"]
            n["chain"] = n.get("chain") or meta["chain"]

    bridge_edges: list[dict[str, Any]] = []
    for e in edges:
        fr_node = id_to_node.get(str(e.get("from")), {})
        to_node = id_to_node.get(str(e.get("to")), {})
        fr_bridge = _bridge_meta(str(fr_node.get("address") or ""))
        to_bridge = _bridge_meta(str(to_node.get("address") or ""))
        if fr_bridge or to_bridge:
            e["edge_type"] = "cross_chain_hop"
            e["bridge_name"] = (to_bridge or fr_bridge or {}).get("name", "bridge")
            e["bridge_confidence"] = 0.75
            bridge_edges.append(e)

    # Heuristic: match outbound bridge transfer to inbound on another chain (amount + time).
    outbound: list[dict[str, Any]] = []
    inbound: list[dict[str, Any]] = []
    for e in bridge_edges:
        to_node = id_to_node.get(str(e.get("to")), {})
        fr_node = id_to_node.get(str(e.get("from")), {})
        if _bridge_meta(str(to_node.get("address") or "")):
            outbound.append({**e, "_chain": fr_node.get("chain"), "_peer": fr_node})
        if _bridge_meta(str(fr_node.get("address") or "")):
            inbound.append({**e, "_chain": to_node.get("chain"), "_peer": to_node})

    for out_e in outbound:
        out_amt = float(out_e.get("amount") or 0)
        out_ts = _norm_ts(out_e.get("timestamp"))
        if not out_amt or not out_ts:
            continue
        for in_e in inbound:
            if in_e.get("_chain") == out_e.get("_chain"):
                continue
            in_amt = float(in_e.get("amount") or 0)
            in_ts = _norm_ts(in_e.get("timestamp"))
            if not in_amt or not in_ts:
                continue
            if abs(in_ts - out_ts) > _CROSS_CHAIN_WINDOW_MS:
                continue
            ratio = min(out_amt, in_amt) / max(out_amt, in_amt) if max(out_amt, in_amt) else 0
            if ratio < 0.85:
                continue
            conf = round(0.45 + 0.4 * ratio, 2)
            link = {
                "from_chain": out_e.get("_chain"),
                "to_chain": in_e.get("_chain"),
                "from_address": (out_e.get("_peer") or {}).get("address"),
                "to_address": (in_e.get("_peer") or {}).get("address"),
                "amount": min(out_amt, in_amt),
                "confidence": conf,
                "bridge_name": out_e.get("bridge_name"),
                "note_ru": f"Эвристика моста · confidence {conf:.0%}",
            }
            cross_links.append(link)
            out_e["bridge_confidence"] = max(float(out_e.get("bridge_confidence") or 0), conf)
            in_e["bridge_confidence"] = max(float(in_e.get("bridge_confidence") or 0), conf)

    graph["cross_chain_links"] = cross_links[:20]


def _norm_ts(ts: Any) -> int | None:
    if ts is None:
        return None
    try:
        v = int(ts)
    except (TypeError, ValueError):
        return None
    if v < 10_000_000_000:
        return v * 1000
    return v


def _build_timeline(graph: dict[str, Any]) -> dict[str, Any] | None:
    """Chronological edge events for timeline slider / play animation."""
    events: list[dict[str, Any]] = []
    for e in graph.get("edges") or []:
        ts = _norm_ts(e.get("timestamp"))
        if ts is None:
            continue
        events.append(
            {
                "ts": ts,
                "edge_id": e.get("id") or f"{e.get('from')}->{e.get('to')}",
                "from": e.get("from"),
                "to": e.get("to"),
                "amount": e.get("amount"),
                "asset": e.get("asset"),
            }
        )
    if not events:
        return None
    events.sort(key=lambda x: x["ts"])
    return {
        "min_ts": events[0]["ts"],
        "max_ts": events[-1]["ts"],
        "event_count": len(events),
        "events": events,
    }


def graph_to_graphml(graph: dict[str, Any], *, view: str = "address") -> str:
    """Export graph as GraphML for Gephi / external analyst tools."""
    active = graph.get("address_view") if view == "address" else graph.get("cluster_view")
    if not active:
        active = graph
    root = Element(
        "graphml",
        attrib={
            "xmlns": "http://graphml.graphdrawing.org/xmlns",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        },
    )
    SubElement(root, "key", id="label", **{"for": "node", "attr.name": "label", "attr.type": "string"})
    SubElement(root, "key", id="chain", **{"for": "node", "attr.name": "chain", "attr.type": "string"})
    SubElement(root, "key", id="risk", **{"for": "node", "attr.name": "risk_score", "attr.type": "double"})
    SubElement(root, "key", id="amount", **{"for": "edge", "attr.name": "amount", "attr.type": "double"})
    g = SubElement(root, "graph", id="finskalp", edgedefault="directed")

    for n in active.get("nodes") or []:
        node_el = SubElement(g, "node", id=str(n.get("id")))
        SubElement(node_el, "data", key="label").text = html.escape(str(n.get("label") or n.get("address") or ""))
        SubElement(node_el, "data", key="chain").text = str(n.get("chain") or "")
        SubElement(node_el, "data", key="risk").text = str(n.get("risk_score") or 0)

    for i, e in enumerate(active.get("edges") or []):
        edge_el = SubElement(
            g,
            "edge",
            id=str(e.get("id") or f"e{i}"),
            source=str(e.get("from")),
            target=str(e.get("to")),
        )
        SubElement(edge_el, "data", key="amount").text = str(e.get("amount") or 0)

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode")
