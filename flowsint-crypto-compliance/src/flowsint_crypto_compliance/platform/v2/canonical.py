"""Canonical domain model — RFC-0002 / RFC-0003 Entity First + Knowledge Graph."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from flowsint_crypto_compliance.platform.v2.relation_types import RelationType


class EntityType(str, Enum):
    """Full RFC-0003 taxonomy (Ch.2) with RFC-0002 backward-compatible members."""

    # Identity & actors
    PERSON = "person"
    ALIAS = "alias"
    USERNAME = "username"
    NICKNAME = "nickname"
    # Organizations
    COMPANY = "company"
    EXCHANGE = "exchange"
    BANK = "bank"
    GOVERNMENT_AGENCY = "gov_agency"
    NGO = "ngo"
    # Digital identifiers
    WALLET = "wallet"
    BLOCKCHAIN_ADDRESS = "blockchain_address"
    SMART_CONTRACT = "smart_contract"
    ENS_DOMAIN = "ens_domain"
    DNS_DOMAIN = "dns_domain"
    EMAIL = "email"
    PHONE = "phone"
    IP_ADDRESS = "ip_address"
    DEVICE_FINGERPRINT = "device_fp"
    # Financial
    TRANSACTION = "transaction"
    ASSET = "asset"
    TOKEN = "token"
    BANK_ACCOUNT = "bank_account"
    CARD = "card"
    # Documents & legal
    PASSPORT = "passport"
    CONTRACT = "contract"
    INVOICE = "invoice"
    COURT_DECISION = "court_decision"
    PDF = "pdf"
    IMAGE = "image"
    OCR_DOCUMENT = "ocr_doc"
    # Sources & media
    TELEGRAM = "telegram"
    FORUM = "forum"
    LEAK = "leak"
    REGISTRY = "registry"
    BLOCKCHAIN_EXPLORER = "explorer"
    SANCTIONS_LIST = "sanctions"
    NEWS = "news"
    SOCIAL_MEDIA = "social"
    # RFC-0002 legacy (retained for backward compatibility)
    ORGANIZATION = "organization"
    DOCUMENT = "document"
    EVIDENCE = "evidence"
    CASE = "case"
    DOMAIN = "domain"
    SANCTION_RECORD = "sanction_record"
    REGISTRY_RECORD = "registry_record"


# Normalization map: legacy / external string → canonical EntityType value
ENTITY_TYPE_ALIASES: dict[str, str] = {
    "organization": EntityType.COMPANY.value,
    "org": EntityType.COMPANY.value,
    "company": EntityType.COMPANY.value,
    "domain": EntityType.DNS_DOMAIN.value,
    "dns": EntityType.DNS_DOMAIN.value,
    "onion": EntityType.DNS_DOMAIN.value,
    "crypto_address": EntityType.BLOCKCHAIN_ADDRESS.value,
    "blockchain_address": EntityType.BLOCKCHAIN_ADDRESS.value,
    "address": EntityType.BLOCKCHAIN_ADDRESS.value,
    "wallet": EntityType.WALLET.value,
    "gov_agency": EntityType.GOVERNMENT_AGENCY.value,
    "government_agency": EntityType.GOVERNMENT_AGENCY.value,
    "device_fingerprint": EntityType.DEVICE_FINGERPRINT.value,
    "device_fp": EntityType.DEVICE_FINGERPRINT.value,
    "ocr_document": EntityType.OCR_DOCUMENT.value,
    "ocr_doc": EntityType.OCR_DOCUMENT.value,
    "blockchain_explorer": EntityType.BLOCKCHAIN_EXPLORER.value,
    "explorer": EntityType.BLOCKCHAIN_EXPLORER.value,
    "sanctions": EntityType.SANCTIONS_LIST.value,
    "sanction_record": EntityType.SANCTIONS_LIST.value,
    "social_media": EntityType.SOCIAL_MEDIA.value,
    "social": EntityType.SOCIAL_MEDIA.value,
    "registry_record": EntityType.REGISTRY.value,
    "username": EntityType.USERNAME.value,
    "person": EntityType.PERSON.value,
    "case": EntityType.CASE.value,
    "document": EntityType.DOCUMENT.value,
    "evidence": EntityType.EVIDENCE.value,
}


def normalize_entity_type(value: str | EntityType) -> EntityType:
    """Resolve legacy aliases to canonical EntityType."""
    if isinstance(value, EntityType):
        return value
    raw = value.strip().lower()
    if raw in ENTITY_TYPE_ALIASES:
        return EntityType(ENTITY_TYPE_ALIASES[raw])
    try:
        return EntityType(raw)
    except ValueError:
        return EntityType.EVIDENCE


class TrustLevel(BaseModel):
    """Admiralty-inspired trust for a single finding."""

    source_reliability: float = Field(ge=0.0, le=1.0, default=0.55)
    information_credibility: float = Field(ge=0.0, le=1.0, default=0.5)
    sample_size: int = 0
    insufficient_data: bool = False

    @property
    def composite(self) -> float:
        if self.insufficient_data:
            return min(self.source_reliability, self.information_credibility) * 0.85
        return self.source_reliability * self.information_credibility


class ConfidenceBreakdown(BaseModel):
    """RFC-0003 Ch.8 — explainable confidence decomposition."""

    composite: float = Field(ge=0.0, le=1.0, default=0.5)
    independent_sources: int = 0
    source_quality: float = Field(ge=0.0, le=1.0, default=0.5)
    freshness: float = Field(ge=0.0, le=1.0, default=0.5)
    consistency: float = Field(ge=0.0, le=1.0, default=0.5)
    explain: dict[str, Any] = Field(default_factory=dict)


class EntityAttribute(BaseModel):
    key: str
    value: Any
    source: str = "unknown"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeRelation(BaseModel):
    """First-class relation — RFC-0003; requires evidence to be a fact."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tenant_id: uuid.UUID
    from_entity_id: uuid.UUID
    to_entity_id: uuid.UUID
    relation_type: str
    source: str = "unknown"
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    acquisition_method: str = "inferred"
    actor: str = "system"
    valid_until: datetime | None = None
    version: int = 1
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)
    flagged_without_evidence: bool = False

    @field_validator("relation_type", mode="before")
    @classmethod
    def _normalize_relation_type(cls, v: Any) -> str:
        if isinstance(v, RelationType):
            return v.value
        return str(v).strip().lower()

    @model_validator(mode="after")
    def _check_evidence(self) -> KnowledgeRelation:
        if not self.evidence_ids:
            self.flagged_without_evidence = True
        return self

    def is_valid_fact(self) -> bool:
        return bool(self.evidence_ids) and not self.flagged_without_evidence


# Backward-compatible alias
EntityRelation = KnowledgeRelation


class Entity(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tenant_id: uuid.UUID
    entity_type: EntityType
    canonical_key: str
    display_name: str = ""
    version: int = 1
    attributes: list[EntityAttribute] = Field(default_factory=list)

    @field_validator("entity_type", mode="before")
    @classmethod
    def _coerce_entity_type(cls, v: Any) -> EntityType:
        if isinstance(v, EntityType):
            return v
        return normalize_entity_type(str(v))

    def with_attribute(self, attr: EntityAttribute) -> Entity:
        return self.model_copy(update={"attributes": [*self.attributes, attr], "version": self.version + 1})


class Evidence(BaseModel):
    """Evidence Center record — RFC-0002 § Evidence Center, RFC-0003 extensions."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tenant_id: uuid.UUID
    case_id: uuid.UUID | None = None
    entity_id: uuid.UUID | None = None
    source_type: str
    content_hash: str
    snapshot_uri: str | None = None
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trust: TrustLevel = Field(default_factory=TrustLevel)
    payload: dict[str, Any] = Field(default_factory=dict)
    # RFC-0003
    acquisition_method: str = "automated_collection"
    digital_signature: str | None = None
    original_uri: str | None = None
    retention_policy: str = "standard_7y"
    valid_until: datetime | None = None
    explain: dict[str, Any] = Field(default_factory=dict)

    @property
    def trust_level(self) -> float:
        return self.trust.composite


class RelationWithoutEvidenceError(ValueError):
    """Raised when a relation is created without supporting evidence."""

    def __init__(self, message: str = "Связь без доказательства не может считаться фактом") -> None:
        super().__init__(message)
