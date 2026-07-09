"""DeFi / DEX router detection for investigation graphs (open contract lists)."""

from __future__ import annotations

from typing import Any

# Routers, factories, known DeFi entry points (public explorer metadata).
_KNOWN_DEFI: dict[str, dict[str, str]] = {
    "0x10ed43c718714eb63d5aa57b78b54704e256024e": {
        "name": "PancakeSwap Router",
        "chain": "bsc",
        "defi_type": "dex_router",
    },
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": {
        "name": "Uniswap V2 Router",
        "chain": "eth",
        "defi_type": "dex_router",
    },
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": {
        "name": "Uniswap V3 Router",
        "chain": "eth",
        "defi_type": "dex_router",
    },
    "tkzxdv2t6kk7k1a48kqvzk1srvde9be9fe": {
        "name": "SunSwap V2 Router",
        "chain": "tron",
        "defi_type": "dex_router",
    },
    "TKzxdv2T6kk7k1a48KQvzk1sRvde9BE9Fe": {
        "name": "SunSwap V2 Router",
        "chain": "tron",
        "defi_type": "dex_router",
    },
}

_DEFI_LOOKUP: dict[str, dict[str, str]] = dict(_KNOWN_DEFI)
for k, v in list(_KNOWN_DEFI.items()):
    _DEFI_LOOKUP[k.lower()] = v


def _norm(addr: str) -> str:
    return (addr or "").strip().lower()


def lookup_defi(address: str) -> dict[str, str] | None:
    a = (address or "").strip()
    return _DEFI_LOOKUP.get(a) or _DEFI_LOOKUP.get(_norm(a))


def annotate_defi(graph: dict[str, Any]) -> dict[str, Any]:
    """Tag DeFi router/LP nodes and swap-like edges."""
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    hits: list[dict[str, Any]] = []

    for n in nodes:
        meta = lookup_defi(str(n.get("address") or ""))
        if not meta:
            continue
        hits.append(
            {
                "address": n.get("address"),
                "chain": n.get("chain"),
                "name": meta["name"],
                "defi_type": meta["defi_type"],
            }
        )
        if n.get("role") == "bridge" or n.get("category") == "bridge":
            n["defi_type"] = meta["defi_type"]
            continue
        n["role"] = "defi"
        n["category"] = "defi"
        n["defi_type"] = meta["defi_type"]
        n["label"] = meta["name"]
        n["chain"] = n.get("chain") or meta["chain"]

    id_to_addr = {str(n["id"]): str(n.get("address") or "") for n in nodes}
    for e in edges:
        fr_addr = id_to_addr.get(str(e.get("from")), "")
        to_addr = id_to_addr.get(str(e.get("to")), "")
        if lookup_defi(fr_addr) or lookup_defi(to_addr):
            e["edge_type"] = e.get("edge_type") or "defi_swap"
            e["defi_interaction"] = True

    graph["defi_hits"] = hits
    graph["defi_detected"] = bool(hits)
    return graph
