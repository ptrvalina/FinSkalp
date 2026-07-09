"""Export fusion investigation graphs as FTM entity + statement bundles."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from flowsint_crypto_compliance.interop.ftm_adapter import _CHAIN_TO_CURRENCY, _stable_ftm_id

_DATASET = "finskalp"


def _node_entity_id(node: dict[str, Any]) -> str:
    chain = str(node.get("chain") or "tron").lower()
    address = str(node.get("address") or node.get("id") or "")
    if address and ":" in address and not address.startswith("0x"):
        address = address.split(":", 1)[-1]
    return _stable_ftm_id(chain, address or str(node.get("id")), _DATASET)


def _wallet_entity(node: dict[str, Any]) -> dict[str, Any]:
    chain = str(node.get("chain") or "tron").lower()
    address = str(node.get("address") or "")
    currency = _CHAIN_TO_CURRENCY.get(chain, chain)
    label = node.get("label") or address[:16] or str(node.get("id"))
    topics: list[str] = []
    if node.get("category"):
        topics.append(str(node["category"]))
    if node.get("sanctioned"):
        topics.append("sanction")

    props: dict[str, Any] = {
        "cryptoWallet": [address] if address else [],
        "currency": [currency],
        "topics": topics,
        "notes": [f"hop={node.get('hop', 0)}", f"risk_score={node.get('risk_score', 0)}"],
    }
    if node.get("role"):
        props["notes"].append(f"role={node['role']}")

    return {
        "id": _node_entity_id(node),
        "schema": "CryptoWallet",
        "caption": label,
        "datasets": [_DATASET],
        "properties": props,
    }


def _edge_statement(edge: dict[str, Any], source_id: str, target_id: str, idx: int) -> dict[str, Any]:
    amount = edge.get("amount") or edge.get("value_usd") or edge.get("volume_usd")
    stmt_id = hashlib.sha256(f"{source_id}:{target_id}:{idx}".encode()).hexdigest()[:20]
    props: dict[str, Any] = {}
    if amount is not None:
        props["amount"] = [str(amount)]
    if edge.get("timestamp"):
        props["date"] = [str(edge["timestamp"])]
    if edge.get("exposure_type"):
        props["notes"] = [f"exposure_type={edge['exposure_type']}"]

    return {
        "id": f"stmt-{stmt_id}",
        "schema": "Payment",
        "entity": source_id,
        "target": target_id,
        "datasets": [_DATASET],
        "properties": props,
    }


def fusion_graph_to_ftm_bundle(graph: dict[str, Any]) -> dict[str, Any]:
    """Build FTM-compatible bundle with entities[] and statements[] from fusion graph."""
    base = graph.get("address_view") or graph
    nodes = base.get("nodes") or []
    edges = base.get("edges") or []

    id_by_node: dict[str, str] = {}
    entities: list[dict[str, Any]] = []
    for node in nodes:
        nid = str(node.get("id") or "")
        if not nid:
            continue
        ent = _wallet_entity(node)
        id_by_node[nid] = ent["id"]
        entities.append(ent)

    statements: list[dict[str, Any]] = []
    for idx, edge in enumerate(edges):
        fr = str(edge.get("from") or "")
        to = str(edge.get("to") or "")
        src = id_by_node.get(fr)
        tgt = id_by_node.get(to)
        if not src or not tgt:
            continue
        statements.append(_edge_statement(edge, src, tgt, idx))

    return {
        "version": "fusion_graph_ftm_export_v1",
        "dataset": _DATASET,
        "entity_count": len(entities),
        "statement_count": len(statements),
        "entities": entities,
        "statements": statements,
    }


def fusion_graph_to_ftm_ndjson(graph: dict[str, Any]) -> str:
    """NDJSON lines: entities first, then statements."""
    bundle = fusion_graph_to_ftm_bundle(graph)
    lines = [json.dumps(row, ensure_ascii=False) for row in bundle["entities"]]
    lines += [json.dumps(row, ensure_ascii=False) for row in bundle["statements"]]
    return "\n".join(lines) + ("\n" if lines else "")
