"""Domain service contracts — RFC-0002 Chapter 10."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from flowsint_crypto_compliance.platform.v2.canonical import Entity, Evidence
from flowsint_crypto_compliance.platform.v2.events import PlatformEvent


@runtime_checkable
class AcquisitionPlugin(Protocol):
    """L1 — fetch raw data only; no analysis."""

    plugin_id: str
    plugin_version: str

    async def acquire(self, *, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Return raw acquisition records (not canonical entities)."""
        ...


@runtime_checkable
class FusionService(Protocol):
    """L2 — route all intelligence through fusion stages."""

    async def process(self, raw_records: list[dict[str, Any]], *, context: dict[str, Any]) -> list[PlatformEvent]:
        ...


@runtime_checkable
class KnowledgeGraphService(Protocol):
    """L3 — persist entities, relations, versions."""

    async def upsert_entity(self, entity: Entity) -> Entity:
        ...

    async def link_relation(self, from_id: str, to_id: str, relation_type: str, *, confidence: float) -> str:
        ...

    async def store_evidence(self, evidence: Evidence) -> Evidence:
        ...


@runtime_checkable
class AnalyticsService(Protocol):
    """L4 — compute risk/patterns on graph only."""

    async def score_entity(self, entity_id: str, *, context: dict[str, Any]) -> dict[str, Any]:
        ...


@runtime_checkable
class InvestigationService(Protocol):
    """L5 — case workflow, human review."""

    async def open_case(self, *, tenant_id: str, case_ref: str, context: dict[str, Any]) -> dict[str, Any]:
        ...

    async def attach_evidence(self, case_id: str, evidence_id: str) -> None:
        ...
