"""
CIS / Russia sovereign coverage model.

Attribution is built only from sovereign RF/CIS sources:
  - domestic regulatory feeds (Rosfinmonitoring 115-FZ list, FIU)
  - licensed local platforms
  - control purchases
  - public blockchain topology + behavioral heuristics
"""

from __future__ import annotations

from enum import Enum


class CISJurisdiction(str, Enum):
    RU = "RU"
    BY = "BY"
    KZ = "KZ"
    KG = "KG"
    UZ = "UZ"
    TJ = "TJ"
    AM = "AM"
    AZ = "AZ"
    MD = "MD"
    GE = "GE"


# Priority chains for CIS cross-border flows (empirical, regulator-facing)
CIS_CHAIN_PRIORITY: tuple[str, ...] = ("tron", "btc", "eth")

# Typical fiat on-ramp channels in CIS (sovereign coverage)
CIS_ONRAMP_CHANNELS: tuple[str, ...] = (
    "p2p_rub",
    "p2p_local_fiat",
    "otc_telegram",
    "otc_messenger",
    "local_exchanger",
    "cash_courier",
    "sbp_transfer",
    "card_mir",
    "licensed_domestic_vex",
)

# Known cross-border corridors (origin → transit → exit)
# Used to score paths when only partial anchors exist
CIS_CORRIDORS: tuple[tuple[str, ...], ...] = (
    ("RU", "KZ", "TR", "AE"),
    ("RU", "GE", "TR"),
    ("RU", "BY", "EU"),
    ("RU", "AM", "EU"),
    ("UZ", "KZ", "TR"),
    ("KZ", "TR", "EU"),
    ("RU", "DO", "US"),  # Caribbean off-ramp pattern
    ("RU", "TR", "EU"),
)

# Domestic (sovereign) evidence sources
class DomesticEvidenceSource(str, Enum):
    FIU_RU = "fiu_ru"
    FIU_CIS = "fiu_cis"
    BANK_115FZ = "bank_115fz"
    LICENSED_VASP = "licensed_vasp"
    CONTROL_PURCHASE = "control_purchase"
    P2P_MONITORING = "p2p_monitoring"
    BLOCKCHAIN_PUBLIC = "blockchain_public"
    BEHAVIORAL_HEURISTIC = "behavioral_heuristic"
    CROSS_BORDER_CORRIDOR = "cross_border_corridor"
    PEER_REGULATOR_EXCHANGE = "peer_regulator_exchange"  # bilateral with KZ, BY, etc.


# Minimum weight to treat a region as "anchored" in sovereign model
REGION_ANCHOR_THRESHOLD = 0.55

# Black-zone structural signals (no external mixer DB required)
BLACK_ZONE_SIGNALS: tuple[str, ...] = (
    "high_fan_in_fan_out",       # payment hub / OTC aggregator
    "peel_chain",                # sequential peel to new addresses
    "round_amount_bursts",       # many similar USDT amounts
    "rapid_layering",            # many hops < 24h
    "trc20_split_merge",         # TRON USDT split pattern
    "btc_coinjoin_like",         # equal-output heuristic
    "cross_chain_hop",           # TRON → bridge-like → ETH/BTC
)
