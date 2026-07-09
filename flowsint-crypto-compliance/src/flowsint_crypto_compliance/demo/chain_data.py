"""In-memory on-chain graph for regulator demo scenarios (TRON / BTC / ETH)."""

from __future__ import annotations

from flowsint_crypto_compliance.chains.base import InMemoryChainAdapter, OnChainTransfer
from flowsint_types.fiat_crypto import Chain

# Scenario 1: P2P RUB → gray → hub → offshore
S1_TRON = [
    OnChainTransfer(Chain.TRON, "s1t1", "TRU_P2P_ENTRY", "TRU_GRAY_A", "USDT", 25000),
    OnChainTransfer(Chain.TRON, "s1t2", "TRU_GRAY_A", "TRU_HUB_MSK", "USDT", 25000),
    OnChainTransfer(Chain.TRON, "s1t3", "TRU_HUB_MSK", "TRU_OFFSHORE_EXIT", "USDT", 24000),
    OnChainTransfer(Chain.TRON, "s1t4", "TRU_HUB_MSK", "TRU_OFFSHORE_EXIT2", "USDT", 1000),
]
S1_BTC = [
    OnChainTransfer(Chain.BTC, "b1t1", "bc1q_p2p_entry_demo", "bc1q_gray_a_demo", "BTC", 0.42),
    OnChainTransfer(Chain.BTC, "b1t2", "bc1q_gray_a_demo", "bc1q_hub_msk_demo", "BTC", 0.42),
    OnChainTransfer(Chain.BTC, "b1t3", "bc1q_hub_msk_demo", "bc1q_offshore_exit", "BTC", 0.40),
]
S1_ETH = [
    OnChainTransfer(Chain.ETH, "e1t1", "0xP2P_ENTRY_DEMO", "0xGRAY_A_DEMO", "USDT", 25000),
    OnChainTransfer(Chain.ETH, "e1t2", "0xGRAY_A_DEMO", "0xHUB_MSK_DEMO", "USDT", 25000),
    OnChainTransfer(Chain.ETH, "e1t3", "0xHUB_MSK_DEMO", "0xOFFSHORE_EXIT", "USDT", 24000),
]

# Scenario 2: RU → KZ transit
S2_TRON = [
    OnChainTransfer(Chain.TRON, "s2t1", "TRU_OTC_RU", "TRU_TRANSIT_1", "USDT", 15000),
    OnChainTransfer(Chain.TRON, "s2t2", "TRU_TRANSIT_1", "TRU_TRANSIT_2", "USDT", 15000),
    OnChainTransfer(Chain.TRON, "s2t3", "TRU_TRANSIT_2", "TKZ_LOCAL_EXIT", "USDT", 15000),
]
S2_BTC = [
    OnChainTransfer(Chain.BTC, "b2t1", "bc1q_otc_ru", "bc1q_transit_1", "BTC", 0.25),
    OnChainTransfer(Chain.BTC, "b2t2", "bc1q_transit_1", "bc1q_transit_2", "BTC", 0.25),
    OnChainTransfer(Chain.BTC, "b2t3", "bc1q_transit_2", "bc1q_kz_exit", "BTC", 0.25),
]

# Scenario 3: RU → layering → Dominican exit
S3_TRON = [
    OnChainTransfer(Chain.TRON, "s3t1", "TRU_P2P_RU2", "TRU_LAYER_1", "USDT", 8000),
    OnChainTransfer(Chain.TRON, "s3t2", "TRU_LAYER_1", "TRU_LAYER_2", "USDT", 8000),
    OnChainTransfer(Chain.TRON, "s3t3", "TRU_LAYER_2", "TDO_CEX_EXIT", "USDT", 8000),
]

# Scenario 4: SBP → gray hub (high fan-out)
S4_TRON_IN = [
    OnChainTransfer(Chain.TRON, f"s4in{i}", f"TRU_SBP_SRC_{i}", "TRU_SBP_HUB", "USDT", 5000)
    for i in range(10)
]
S4_TRON_OUT = [
    OnChainTransfer(Chain.TRON, f"s4out{i}", "TRU_SBP_HUB", f"TRU_SBP_DST_{i}", "USDT", 5000)
    for i in range(10)
]
S4_BTC_IN = [
    OnChainTransfer(Chain.BTC, f"b4in{i}", f"bc1q_sbp_src_{i}", "bc1q_sbp_hub", "BTC", 0.08)
    for i in range(10)
]
S4_BTC_OUT = [
    OnChainTransfer(Chain.BTC, f"b4out{i}", "bc1q_sbp_hub", f"bc1q_sbp_dst_{i}", "BTC", 0.08)
    for i in range(10)
]

DEMO_TRANSFERS: dict[str, dict[Chain, list[OnChainTransfer]]] = {
    "p2p_rub_offshore": {
        Chain.TRON: S1_TRON,
        Chain.BTC: S1_BTC,
        Chain.ETH: S1_ETH,
    },
    "cis_transit_kz": {
        Chain.TRON: S2_TRON,
        Chain.BTC: S2_BTC,
    },
    "cross_border_do": {Chain.TRON: S3_TRON},
    "sbp_gray_hub": {
        Chain.TRON: S4_TRON_IN + S4_TRON_OUT,
        Chain.BTC: S4_BTC_IN + S4_BTC_OUT,
    },
}

ALL_BY_CHAIN: dict[Chain, list[OnChainTransfer]] = {
    Chain.TRON: S1_TRON + S2_TRON + S3_TRON + S4_TRON_IN + S4_TRON_OUT,
    Chain.BTC: S1_BTC + S2_BTC + S4_BTC_IN + S4_BTC_OUT,
    Chain.ETH: S1_ETH,
}


def get_demo_adapters(scenario_id: str | None = None) -> dict[Chain, InMemoryChainAdapter]:
    """Return in-memory chain adapters — no live Blockstream/Etherscan/TronGrid."""
    if scenario_id and scenario_id in DEMO_TRANSFERS:
        per_chain = DEMO_TRANSFERS[scenario_id]
    else:
        per_chain = ALL_BY_CHAIN
    return {
        chain: InMemoryChainAdapter(chain, txs)
        for chain, txs in per_chain.items()
    }
