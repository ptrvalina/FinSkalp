"""Blockchain chain registry and capabilities — RFC-0004 Ch.2."""

from __future__ import annotations

from typing import Any

from flowsint_types.fiat_crypto import Chain

from flowsint_crypto_compliance.chains.base import ChainAdapter, InMemoryChainAdapter
from flowsint_crypto_compliance.chains.btc import BtcChainAdapter
from flowsint_crypto_compliance.chains.eth import EthChainAdapter
from flowsint_crypto_compliance.chains.evm_blockscout import EvmBlockscoutAdapter
from flowsint_crypto_compliance.chains.ltc import LtcChainAdapter
from flowsint_crypto_compliance.chains.sol_chain import SolanaChainAdapter
from flowsint_crypto_compliance.chains.tron import TronChainAdapter

RFC_CHAIN_CAPABILITIES = (
    "import_addresses",
    "import_transactions",
    "import_tokens",
    "smart_contract_analysis",
    "service_detection",
    "cluster_search",
    "mixer_detection",
    "bridge_analysis",
    "flow_calculation",
)

CHAIN_REGISTRY: dict[str, dict[str, Any]] = {
    "btc": {"chain": Chain.BTC, "status": "production", "label_ru": "Bitcoin"},
    "eth": {"chain": Chain.ETH, "status": "production", "label_ru": "Ethereum"},
    "tron": {"chain": Chain.TRON, "status": "production", "label_ru": "Tron"},
    "sol": {"chain": Chain.SOL, "status": "production", "label_ru": "Solana"},
    "ltc": {"chain": Chain.LTC, "status": "production", "label_ru": "Litecoin"},
    "bsc": {"chain": Chain.BSC, "status": "production", "label_ru": "BNB Chain"},
    "bnb": {"chain": Chain.BSC, "status": "production", "label_ru": "BNB Chain"},
    "polygon": {"chain": Chain.POLYGON, "status": "production", "label_ru": "Polygon"},
}


def normalize_chain_key(chain: str | None) -> str:
    if not chain:
        return "unknown"
    key = chain.strip().lower()
    if key in ("bnb", "binance"):
        return "bsc"
    return key


def get_chain_adapter_by_key(chain_key: str, *, use_memory: bool = False) -> ChainAdapter | None:
    """Resolve adapter for RFC-0004 priority chains."""
    key = normalize_chain_key(chain_key)
    if use_memory:
        meta = CHAIN_REGISTRY.get(key)
        if not meta:
            return None
        return InMemoryChainAdapter(meta["chain"], [])

    try:
        if key == "btc":
            return BtcChainAdapter()
        if key == "eth":
            return EthChainAdapter()
        if key == "tron":
            return TronChainAdapter()
        if key == "sol":
            return SolanaChainAdapter()
        if key == "ltc":
            return LtcChainAdapter()
        if key in ("bsc", "bnb", "polygon"):
            return EvmBlockscoutAdapter(key)
    except Exception:
        meta = CHAIN_REGISTRY.get(key)
        if meta:
            return InMemoryChainAdapter(meta["chain"], [])
    return None


def blockchain_capabilities_manifest() -> dict[str, Any]:
    chains = []
    for key, meta in CHAIN_REGISTRY.items():
        if key == "bnb":
            continue
        chains.append(
            {
                "chain": key,
                "label_ru": meta["label_ru"],
                "status": meta["status"],
                "capabilities": list(RFC_CHAIN_CAPABILITIES),
            }
        )
    return {
        "priority_chains": ["btc", "eth", "tron", "ltc", "bsc", "polygon", "sol"],
        "chains": chains,
        "capabilities": list(RFC_CHAIN_CAPABILITIES),
    }
