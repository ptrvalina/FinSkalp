"""RFC-0012 Ch.4 — canonical blockchain model."""

from __future__ import annotations

from enum import Enum
from typing import Any

CANONICAL_ENTITIES = (
    "Network",
    "Block",
    "Transaction",
    "Address",
    "Asset",
    "Token",
    "SmartContract",
    "Transfer",
    "Fee",
    "Event",
)

SUPPORTED_NETWORKS = [
    {"id": "btc", "label_ru": "Bitcoin", "model": "utxo"},
    {"id": "eth", "label_ru": "Ethereum", "model": "account"},
    {"id": "tron", "label_ru": "Tron", "model": "account"},
    {"id": "bsc", "label_ru": "BNB Smart Chain", "model": "account"},
    {"id": "polygon", "label_ru": "Polygon", "model": "account"},
    {"id": "ltc", "label_ru": "Litecoin", "model": "utxo"},
    {"id": "sol", "label_ru": "Solana", "model": "account"},
]

PIPELINE_STAGES = [
    "source",
    "adapter",
    "normalizer",
    "validator",
    "entity_resolution",
    "knowledge_graph",
    "risk_engine",
    "timeline",
]

CLUSTERING_METHODS = [
    "utxo_heuristics",
    "usage_patterns",
    "shared_counterparties",
    "temporal_correlation",
    "external_attribution",
]


class CanonicalEntity(str, Enum):
    NETWORK = "Network"
    BLOCK = "Block"
    TRANSACTION = "Transaction"
    ADDRESS = "Address"
    ASSET = "Asset"
    TOKEN = "Token"
    SMART_CONTRACT = "SmartContract"
    TRANSFER = "Transfer"
    FEE = "Fee"
    EVENT = "Event"


def transfer_to_canonical(
    *,
    chain: str,
    tx_hash: str,
    source: str,
    target: str,
    asset: str | None = None,
    amount: float | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    return {
        "entity": CanonicalEntity.TRANSFER.value,
        "network": chain,
        "transaction": {"entity": CanonicalEntity.TRANSACTION.value, "hash": tx_hash},
        "source": {"entity": CanonicalEntity.ADDRESS.value, "value": source},
        "target": {"entity": CanonicalEntity.ADDRESS.value, "value": target},
        "asset": {"entity": CanonicalEntity.ASSET.value, "symbol": asset},
        "amount": amount,
        "timestamp": timestamp,
    }
