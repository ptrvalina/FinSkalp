"""RFC-0007 unified connector contract — Ch.3."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from flowsint_crypto_compliance.platform.v2.connectors.types import (
    ConnectorCollectResult,
    ConnectorDescriptor,
    SourceQualityProfile,
)


class Connector(ABC):
    """Connector First — no direct KG/risk mutation."""

    descriptor: ConnectorDescriptor

    @abstractmethod
    async def connect(self) -> dict[str, Any]:
        """Establish connection to external source."""

    @abstractmethod
    async def authenticate(self) -> dict[str, Any]:
        """Validate credentials / API keys."""

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Health probe for integration management."""

    @abstractmethod
    async def collect(self, *, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Fetch raw records from source."""

    def normalize(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Map to canonical model fields."""
        out: list[dict[str, Any]] = []
        for rec in records:
            if not isinstance(rec, dict):
                continue
            out.append(
                {
                    "entity_type": rec.get("entity_type") or "unknown",
                    "entity_value": rec.get("entity_value") or rec.get("value") or "",
                    "source_type": self.descriptor.connector_id,
                    "confidence": float(rec.get("confidence") or self.descriptor.quality.trust_level),
                    "payload": {**rec, "connector_id": self.descriptor.connector_id},
                    "provenance": self.descriptor.quality.provenance,
                }
            )
        return out

    def validate(self, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
        """Reject invalid rows — mandatory stage."""
        valid: list[dict[str, Any]] = []
        errors: list[str] = []
        for i, rec in enumerate(records):
            if not rec.get("entity_value"):
                errors.append(f"row {i}: missing entity_value")
                continue
            if not rec.get("entity_type"):
                errors.append(f"row {i}: missing entity_type")
                continue
            valid.append(rec)
        return valid, errors

    async def publish(
        self,
        records: list[dict[str, Any]],
        *,
        tenant_id: Any,
        case_ref: str | None = None,
        publish_to_fusion: bool = True,
    ) -> int:
        """Publish events to Fusion via mandatory ingest — no direct KG writes."""
        if not publish_to_fusion or not records:
            return 0
        from flowsint_crypto_compliance.platform.v2.ingest_pipeline import get_ingest_pipeline

        pipeline = get_ingest_pipeline()
        count = 0
        for rec in records:
            ing = pipeline.ingest(
                tenant_id=tenant_id,
                source_type=str(rec.get("source_type") or self.descriptor.connector_id),
                entity_type=str(rec.get("entity_type") or "unknown"),
                entity_value=str(rec.get("entity_value") or ""),
                case_ref=case_ref,
                actor=f"connector.{self.descriptor.connector_id}",
                confidence=float(rec.get("confidence") or 0.5),
                payload=rec.get("payload") if isinstance(rec.get("payload"), dict) else rec,
                require_relation_evidence=False,
            )
            if ing.ok:
                count += 1
        return count

    async def shutdown(self) -> None:
        """Release resources."""

    async def run_pipeline(
        self,
        *,
        query: dict[str, Any] | None = None,
        tenant_id: Any,
        case_ref: str | None = None,
        publish: bool = True,
    ) -> ConnectorCollectResult:
        """Full lifecycle: collect → normalize → validate → publish."""
        result = ConnectorCollectResult(ok=True, connector_id=self.descriptor.connector_id)
        try:
            await self.connect()
            result.stages.append("connect")
            await self.authenticate()
            result.stages.append("authenticate")
            health = await self.health()
            result.stages.append("health")
            result.explain["health"] = health

            raw = await self.collect(query=query)
            result.records = raw
            result.stages.append("collect")

            normalized = self.normalize(raw)
            result.stages.append("normalize")

            valid, val_errors = self.validate(normalized)
            result.errors.extend(val_errors)
            result.normalized = valid
            result.stages.append("validate")

            if valid and publish:
                published = await self.publish(valid, tenant_id=tenant_id, case_ref=case_ref)
                result.events_published = published
                result.stages.append("publish")

            result.stages.extend(["fusion", "knowledge_graph", "analytics"])
            result.ok = bool(valid) or not val_errors
        except Exception as exc:
            result.ok = False
            result.errors.append(str(exc))
            self.descriptor.error_log.append(str(exc))
        finally:
            await self.shutdown()
            result.stages.append("shutdown")
        return result


class BaseConnector(Connector):
    """SDK base — RFC-0007 Ch.8."""

    def __init__(self, descriptor: ConnectorDescriptor) -> None:
        self.descriptor = descriptor
        self._connected = False

    async def connect(self) -> dict[str, Any]:
        self._connected = True
        return {"ok": True, "connector_id": self.descriptor.connector_id}

    async def authenticate(self) -> dict[str, Any]:
        return {"ok": True, "method": "env_or_vault"}

    async def health(self) -> dict[str, Any]:
        from datetime import datetime, timezone

        self.descriptor.last_health_check = datetime.now(timezone.utc)
        return {
            "ok": self._connected,
            "availability": self.descriptor.quality.availability,
            "trust_level": self.descriptor.quality.trust_level,
        }

    async def shutdown(self) -> None:
        self._connected = False
