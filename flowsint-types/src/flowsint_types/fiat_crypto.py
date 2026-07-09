from enum import Enum
from typing import Any, List, Optional, Self

from pydantic import Field, model_validator

from .flowsint_base import FlowsintType
from .registry import flowsint_type


class Chain(str, Enum):
    BTC = "btc"
    ETH = "eth"
    TRON = "tron"
    SOL = "sol"
    LTC = "ltc"
    BSC = "bsc"
    POLYGON = "polygon"


class EntityKind(str, Enum):
    CEX = "cex"
    OTC = "otc"
    P2P = "p2p"
    BRIDGE = "bridge"
    MIXER = "mixer"
    UNKNOWN = "unknown"


class EvidenceSource(str, Enum):
    FIU_ALERT = "fiu_alert"
    BANK_ALERT = "bank_alert"
    LICENSED_PLATFORM = "licensed_platform"
    CONTROL_PURCHASE = "control_purchase"
    BLOCKCHAIN = "blockchain"
    OSINT = "osint"
    SOVEREIGN_REGISTRY = "sovereign_registry"
    BANK_REGULATOR_HUB = "bank_regulator_hub"


class RegistrySource(str, Enum):
    """Sovereign RF/CIS sources for on-chain address risk labels."""

    ROSFINMONITORING = "rosfinmonitoring"  # перечень 115-ФЗ (террористы/экстремисты)
    CBR = "cbr"  # Банк России
    FIU = "fiu"  # финансовая разведка / уполномоченный орган
    MVD = "mvd"  # правоохранительные органы
    BANK_HUB = "bank_hub"  # банковский хаб регулятора
    CONTROL_PURCHASE = "control_purchase"  # контрольная закупка
    INTERNAL_OSINT = "internal_osint"  # собственная OSINT-разведка
    CIS_PARTNER = "cis_partner"  # обмен с ФИУ стран СНГ
    OTHER = "other"


class WalletRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@flowsint_type
class FiatLegEvent(FlowsintType):
    """Fiat-side signal: bank or FIU alert tied to crypto activity."""

    event_id: str = Field(
        ...,
        description="Unique event identifier",
        title="Event ID",
        json_schema_extra={"primary": True},
    )
    source: EvidenceSource = Field(
        ..., description="Origin of the fiat signal", title="Source"
    )
    region: Optional[str] = Field(
        None, description="Geographic region (ISO country or regulator zone)", title="Region"
    )
    currency: Optional[str] = Field(None, description="Fiat currency", title="Currency")
    amount: Optional[float] = Field(None, description="Fiat amount", title="Amount")
    bank_reference: Optional[str] = Field(
        None, description="Bank or payment reference", title="Bank Reference"
    )
    platform_id: Optional[str] = Field(
        None, description="Licensed platform identifier if known", title="Platform ID"
    )
    subject_id: Optional[str] = Field(
        None, description="Pseudonymized subject or case reference", title="Subject ID"
    )
    observed_at: Optional[str] = Field(
        None, description="Observation timestamp (ISO 8601)", title="Observed At"
    )
    raw_summary: Optional[str] = Field(
        None, description="Sanitized summary for investigators", title="Summary"
    )

    @model_validator(mode="after")
    def compute_label(self) -> Self:
        parts = [self.event_id]
        if self.region:
            parts.append(self.region)
        self.nodeLabel = " | ".join(parts)
        return self

    @classmethod
    def detect(cls, line: str) -> bool:
        return False


@flowsint_type
class LicensedPlatformEvent(FlowsintType):
    """Deposit or withdrawal on a licensed crypto platform."""

    event_id: str = Field(
        ...,
        description="Platform event identifier",
        title="Event ID",
        json_schema_extra={"primary": True},
    )
    platform_name: str = Field(..., description="Licensed platform name", title="Platform")
    platform_license_id: Optional[str] = Field(
        None, description="Regulator license number", title="License ID"
    )
    region: Optional[str] = Field(None, description="Platform jurisdiction", title="Region")
    direction: str = Field(
        ..., description="deposit or withdrawal", title="Direction"
    )
    chain: Chain = Field(..., description="Blockchain network", title="Chain")
    address: str = Field(..., description="On-chain address", title="Address")
    amount_crypto: Optional[float] = Field(
        None, description="Crypto amount", title="Crypto Amount"
    )
    asset: Optional[str] = Field(None, description="Asset symbol (USDT, BTC, ...)", title="Asset")
    amount_fiat: Optional[float] = Field(None, description="Fiat equivalent", title="Fiat Amount")
    currency: Optional[str] = Field(None, description="Fiat currency", title="Currency")
    user_ref: Optional[str] = Field(
        None, description="Pseudonymized platform user reference", title="User Ref"
    )
    observed_at: Optional[str] = Field(None, description="Event timestamp", title="Observed At")

    @model_validator(mode="after")
    def compute_label(self) -> Self:
        self.nodeLabel = f"{self.platform_name} {self.direction} {self.address[:12]}..."
        return self

    @classmethod
    def detect(cls, line: str) -> bool:
        return False


@flowsint_type
class ControlPurchaseEvent(FlowsintType):
    """Controlled purchase used to ground gray addresses."""

    event_id: str = Field(
        ...,
        description="Control purchase identifier",
        title="Event ID",
        json_schema_extra={"primary": True},
    )
    operator_ref: str = Field(
        ..., description="Investigator or unit reference", title="Operator"
    )
    region: str = Field(..., description="Purchase region", title="Region")
    channel: str = Field(
        ..., description="P2P, OTC, ATM, local exchange, etc.", title="Channel"
    )
    chain: Chain = Field(..., description="Blockchain network", title="Chain")
    source_address: Optional[str] = Field(
        None, description="Address funds were sent from", title="Source Address"
    )
    target_address: str = Field(
        ..., description="Address that received controlled funds", title="Target Address"
    )
    asset: Optional[str] = Field(None, description="Asset purchased", title="Asset")
    amount_fiat: Optional[float] = Field(None, description="Fiat spent", title="Fiat Amount")
    currency: Optional[str] = Field(None, description="Fiat currency", title="Currency")
    observed_at: Optional[str] = Field(None, description="Purchase timestamp", title="Observed At")
    notes: Optional[str] = Field(None, description="Operational notes", title="Notes")

    @model_validator(mode="after")
    def compute_label(self) -> Self:
        self.nodeLabel = f"CP {self.region} → {self.target_address[:12]}..."
        return self

    @classmethod
    def detect(cls, line: str) -> bool:
        return False


@flowsint_type
class CryptoCluster(FlowsintType):
    """Probabilistic cluster of on-chain addresses with regional and entity hints."""

    cluster_id: str = Field(
        ...,
        description="Stable cluster identifier",
        title="Cluster ID",
        json_schema_extra={"primary": True},
    )
    label: Optional[str] = Field(
        None, description="Human-readable label (e.g. CEX_cluster_42)", title="Label"
    )
    entity_kind: EntityKind = Field(
        EntityKind.UNKNOWN, description="Inferred entity type", title="Entity Kind"
    )
    claimed_entity: Optional[str] = Field(
        None, description="Self-attributed or KYT entity name", title="Claimed Entity"
    )
    disputed: bool = Field(
        False, description="Entity disputes this attribution", title="Disputed"
    )
    region_weights: Optional[dict[str, float]] = Field(
        None,
        description="Region affinity scores 0..1 (e.g. {'RU': 0.7, 'IN': 0.2})",
        title="Region Weights",
    )
    confidence: float = Field(
        0.0, description="Overall cluster confidence 0..1", title="Confidence"
    )
    member_addresses: Optional[List[str]] = Field(
        None, description="Sample of member addresses", title="Members"
    )
    evidence_sources: Optional[List[EvidenceSource]] = Field(
        None, description="Sources contributing to this cluster", title="Evidence"
    )

    @model_validator(mode="after")
    def compute_label(self) -> Self:
        parts = [self.label or self.cluster_id]
        if self.claimed_entity:
            parts.append(self.claimed_entity)
        if self.disputed:
            parts.append("(спорно)")
        self.nodeLabel = " — ".join(parts)
        return self

    @classmethod
    def detect(cls, line: str) -> bool:
        return False


@flowsint_type
class FiatCryptoBridge(FlowsintType):
    """Linked bridge between a fiat signal and on-chain movement."""

    bridge_id: str = Field(
        ...,
        description="Bridge link identifier",
        title="Bridge ID",
        json_schema_extra={"primary": True},
    )
    fiat_event_id: str = Field(..., description="Fiat leg event ID", title="Fiat Event")
    chain: Chain = Field(..., description="Blockchain network", title="Chain")
    entry_address: Optional[str] = Field(
        None, description="First observed on-chain address", title="Entry Address"
    )
    exit_address: Optional[str] = Field(
        None, description="Last observed or destination address", title="Exit Address"
    )
    cluster_id: Optional[str] = Field(
        None, description="Associated cluster if resolved", title="Cluster ID"
    )
    hop_count: Optional[int] = Field(
        None, description="On-chain hops between entry and exit", title="Hops"
    )
    region_origin: Optional[str] = Field(
        None, description="Inferred origin region", title="Origin Region"
    )
    region_destination: Optional[str] = Field(
        None, description="Inferred destination region", title="Destination Region"
    )
    confidence: float = Field(
        0.0, description="Bridge confidence score 0..1", title="Confidence"
    )
    evidence: Optional[List[str]] = Field(
        None, description="Human-readable evidence chain", title="Evidence"
    )

    @model_validator(mode="after")
    def compute_label(self) -> Self:
        origin = self.region_origin or "?"
        dest = self.region_destination or "?"
        self.nodeLabel = f"{origin} → {dest} ({self.confidence:.0%})"
        return self

    @classmethod
    def detect(cls, line: str) -> bool:
        return False


@flowsint_type
class BankRegulatorFeed(FlowsintType):
    """Normalized bank signal delivered via government regulator hub (115-FZ)."""

    feed_id: str = Field(
        ...,
        description="Regulator hub record ID",
        title="Feed ID",
        json_schema_extra={"primary": True},
    )
    bank_bic: Optional[str] = Field(None, description="Bank BIC/SWIFT", title="Bank BIC")
    bank_name: Optional[str] = Field(None, description="Reporting bank", title="Bank Name")
    alert_type: Optional[str] = Field(
        None, description="STR, CTR, crypto_suspicion, etc.", title="Alert Type"
    )
    region: str = Field(..., description="Jurisdiction", title="Region")
    currency: Optional[str] = Field(None, description="Fiat currency", title="Currency")
    amount: Optional[float] = Field(None, description="Transaction amount", title="Amount")
    payment_reference: Optional[str] = Field(
        None, description="Payment reference hash", title="Reference"
    )
    counterparty_hint: Optional[str] = Field(
        None, description="Masked counterparty hint", title="Counterparty"
    )
    linked_crypto_address: Optional[str] = Field(
        None, description="Crypto address if bank reported it", title="Crypto Address"
    )
    linked_chain: Optional[Chain] = Field(None, description="Chain if known", title="Chain")
    subject_id: Optional[str] = Field(
        None, description="Pseudonymized subject", title="Subject ID"
    )
    case_id: Optional[str] = Field(None, description="Regulator case ID", title="Case ID")
    observed_at: Optional[str] = Field(None, description="Event timestamp", title="Observed At")

    @model_validator(mode="after")
    def compute_label(self) -> Self:
        bank = self.bank_name or self.bank_bic or "bank"
        self.nodeLabel = f"{bank} | {self.region} | {self.feed_id}"
        return self

    @classmethod
    def detect(cls, line: str) -> bool:
        return False


@flowsint_type
class SovereignRiskLabel(FlowsintType):
    """Risk/attribution label on an on-chain address from sovereign RF/CIS sources.

    Built only from domestic data (Rosfinmonitoring 115-FZ list, FIU/CBR, bank hub,
    control purchases, internal OSINT, bilateral CIS exchange). No foreign vendors.
    """

    label_id: str = Field(
        ...,
        description="Unique label record ID",
        title="Label ID",
        json_schema_extra={"primary": True},
    )
    source: RegistrySource = Field(
        ..., description="Sovereign data source", title="Source"
    )
    chain: Chain = Field(..., description="Blockchain", title="Chain")
    address: str = Field(..., description="On-chain address", title="Address")
    entity_name: Optional[str] = Field(
        None, description="Attributed entity (domestic label)", title="Entity"
    )
    category: Optional[str] = Field(
        None, description="otc, mixer, scam, sanctioned, etc.", title="Category"
    )
    risk_score: Optional[float] = Field(
        None, description="Sovereign risk score 0..100", title="Risk Score"
    )
    confidence: float = Field(
        0.5, description="Source confidence 0..1", title="Confidence"
    )
    sanctioned: bool = Field(
        False,
        description="Address is in the Rosfinmonitoring 115-FZ / official sanctions list",
        title="Sanctioned",
    )
    list_reference: Optional[str] = Field(
        None,
        description="Reference in the official list (e.g. Rosfinmonitoring entry №)",
        title="List Reference",
    )
    disputed: bool = Field(
        False, description="Attribution disputed and pending review", title="Disputed"
    )
    snapshot_at: Optional[str] = Field(
        None, description="Registry snapshot timestamp", title="Snapshot At"
    )
    cluster_ref: Optional[str] = Field(
        None, description="Sovereign cluster ID", title="Cluster Ref"
    )

    @model_validator(mode="after")
    def compute_label(self) -> Self:
        entity = self.entity_name or self.category or "без метки"
        flag = "⛔ " if self.sanctioned else ""
        self.nodeLabel = f"{flag}{self.source.value}: {entity} ({self.address[:10]}...)"
        return self

    @classmethod
    def detect(cls, line: str) -> bool:
        return False


@flowsint_type
class FusedAttribution(FlowsintType):
    """Final merged attribution: sovereign engine + sovereign registry + bank linkage."""

    attribution_id: str = Field(
        ...,
        description="Fused attribution ID",
        title="Attribution ID",
        json_schema_extra={"primary": True},
    )
    address: str = Field(..., description="On-chain address", title="Address")
    chain: Chain = Field(..., description="Blockchain", title="Chain")
    primary_region: Optional[str] = Field(None, title="Primary Region")
    region_weights: Optional[dict[str, float]] = Field(None, title="Region Weights")
    entity_kind: EntityKind = Field(EntityKind.UNKNOWN, title="Entity Kind")
    sovereign_label: Optional[str] = Field(
        None, description="Label from domestic engine", title="Sovereign Label"
    )
    watchlist_label: Optional[str] = Field(
        None,
        description="Label from sovereign registry/watchlist if present",
        title="Watchlist Label",
    )
    label_source: Optional[str] = Field(
        None, description="Sovereign registry source", title="Label Source"
    )
    sanctioned: bool = Field(
        False, description="Address in 115-FZ / official sanctions list", title="Sanctioned"
    )
    list_reference: Optional[str] = Field(None, title="List Reference")
    disputed: bool = Field(False, title="Disputed")
    confidence: float = Field(0.0, title="Fused Confidence")
    gray_zone: bool = Field(True, title="Gray Zone")
    black_zone: bool = Field(False, title="Black Zone")
    bank_feed_ids: Optional[List[str]] = Field(
        None, description="Linked bank regulator feeds", title="Bank Feeds"
    )
    case_id: Optional[str] = Field(None, title="Case ID")
    evidence_chain: Optional[List[str]] = Field(None, title="Evidence Chain")
    linkage_strength: Optional[float] = Field(
        None, description="Bank-crypto linkage score 0..1", title="Linkage Strength"
    )

    @model_validator(mode="after")
    def compute_label(self) -> Self:
        label = self.sovereign_label or self.watchlist_label or self.address[:12]
        flag = "⛔ " if self.sanctioned else ""
        self.nodeLabel = f"{flag}{label} ({self.confidence:.0%})"
        return self

    @classmethod
    def detect(cls, line: str) -> bool:
        return False


@flowsint_type
class WalletScreeningResult(FlowsintType):
    """Operational wallet screening result for first-look compliance checks."""

    screening_id: str = Field(
        ...,
        description="Stable screening identifier",
        title="Screening ID",
        json_schema_extra={"primary": True},
    )
    address: str = Field(..., description="Screened wallet address", title="Address")
    chain: Chain = Field(..., description="Detected blockchain network", title="Chain")
    risk_score: float = Field(0.0, description="Risk score 0..100", title="Risk Score")
    risk_level: WalletRiskLevel = Field(
        WalletRiskLevel.UNKNOWN, description="Risk level", title="Risk Level"
    )
    confidence: float = Field(
        0.0, description="Confidence of the screening result 0..1", title="Confidence"
    )
    summary_ru: str = Field(..., description="Investigator summary", title="Summary")
    findings: List[dict[str, Any]] = Field(
        default_factory=list, description="Structured findings", title="Findings"
    )
    evidence_chain: List[str] = Field(
        default_factory=list, description="Evidence chain", title="Evidence"
    )
    source_status: dict[str, str] = Field(
        default_factory=dict, description="Source health/status map", title="Sources"
    )
    onchain_summary: dict[str, Any] = Field(
        default_factory=dict, description="On-chain aggregate summary", title="On-chain"
    )
    recommendations_ru: List[str] = Field(
        default_factory=list,
        description="Recommended investigator actions",
        title="Recommendations",
    )
    limitations_ru: List[str] = Field(
        default_factory=list,
        description="Explicit limitations and safety notes",
        title="Limitations",
    )

    @model_validator(mode="after")
    def compute_label(self) -> Self:
        self.nodeLabel = f"{self.chain.value}:{self.address[:12]}… риск {self.risk_score:.0f}"
        return self

    @classmethod
    def detect(cls, line: str) -> bool:
        return False
