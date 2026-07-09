from flowsint_types.fiat_crypto import Chain

from .base import ChainAdapter, InMemoryChainAdapter
from .btc import BtcChainAdapter
from .eth import EthChainAdapter
from .evm_blockscout import EvmBlockscoutAdapter
from .ltc import LtcChainAdapter
from .sol_chain import SolanaChainAdapter
from .tron import TronChainAdapter


def get_chain_adapter(chain: Chain, *, use_memory: bool = False) -> ChainAdapter:
    if use_memory:
        return InMemoryChainAdapter(chain, [])
    if chain == Chain.TRON:
        return TronChainAdapter()
    if chain == Chain.ETH:
        return EthChainAdapter()
    if chain == Chain.BTC:
        return BtcChainAdapter()
    if chain == Chain.SOL:
        return SolanaChainAdapter()
    if chain == Chain.LTC:
        return LtcChainAdapter()
    if chain == Chain.BSC:
        return EvmBlockscoutAdapter("bsc")
    if chain == Chain.POLYGON:
        return EvmBlockscoutAdapter("polygon")
    raise ValueError(f"Unsupported chain: {chain}")


def get_chain_adapter_for_key(chain_key: str, *, use_memory: bool = False) -> ChainAdapter:
    from flowsint_crypto_compliance.platform.v2.intelligence.blockchain_capabilities import (
        get_chain_adapter_by_key,
    )

    adapter = get_chain_adapter_by_key(chain_key, use_memory=use_memory)
    if adapter is None:
        raise ValueError(f"Unsupported chain key: {chain_key}")
    return adapter
