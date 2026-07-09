"""RFC-0007 Connector types and quality profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ConnectorCategory(str, Enum):
    BLOCKCHAIN = "blockchain"
    BLOCKCHAIN_INTELLIGENCE = "blockchain_intelligence"
    PUBLIC_EXPLORER = "public_explorer"
    REGISTRY = "registry"
    OSINT = "osint"
    DOCUMENT = "document"


class ConnectorStatus(str, Enum):
    PRODUCTION = "production"
    LICENSED = "licensed"
    PLANNED = "planned"
    DISABLED = "disabled"


@dataclass
class SourceQualityProfile:
    """RFC-0007 Ch.6 — source quality metrics."""

    provenance: str = "unknown"
    official: bool = False
    update_frequency: str = "unknown"
    completeness: float = 0.5
    stability: float = 0.5
    trust_level: float = 0.5
    error_rate: float = 0.0
    availability: float = 1.0
    schema_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance,
            "official": self.official,
            "update_frequency": self.update_frequency,
            "completeness": self.completeness,
            "stability": self.stability,
            "trust_level": self.trust_level,
            "error_rate": self.error_rate,
            "availability": self.availability,
            "schema_version": self.schema_version,
        }


@dataclass
class ConnectorDescriptor:
    connector_id: str
    category: ConnectorCategory
    title_ru: str
    version: str = "1.0.0"
    status: ConnectorStatus = ConnectorStatus.PRODUCTION
    author: str = "flowsint"
    license: str = "internal"
    apis: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    quality: SourceQualityProfile = field(default_factory=SourceQualityProfile)
    last_health_check: datetime | None = None
    error_log: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "category": self.category.value,
            "title_ru": self.title_ru,
            "version": self.version,
            "status": self.status.value,
            "author": self.author,
            "license": self.license,
            "apis": self.apis,
            "constraints": self.constraints,
            "quality": self.quality.to_dict(),
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "error_log_count": len(self.error_log),
        }


@dataclass
class ConnectorCollectResult:
    ok: bool
    connector_id: str
    records: list[dict[str, Any]] = field(default_factory=list)
    normalized: list[dict[str, Any]] = field(default_factory=list)
    events_published: int = 0
    stages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "connector_id": self.connector_id,
            "record_count": len(self.records),
            "normalized_count": len(self.normalized),
            "events_published": self.events_published,
            "stages": self.stages,
            "errors": self.errors,
            "explain": self.explain,
        }
