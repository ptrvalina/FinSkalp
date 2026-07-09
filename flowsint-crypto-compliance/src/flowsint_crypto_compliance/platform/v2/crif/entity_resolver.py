"""RFC-0015 Ch.6 — entity resolver delegating to entity_resolution.py (no KG writes)."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.entity_resolution import EntityResolutionEngine


class CRIFEntityResolver:
    """Resolve registry entities via EntityResolutionEngine — read-only, no graph mutation."""

    def __init__(self, engine: EntityResolutionEngine | None = None) -> None:
        self._engine = engine or EntityResolutionEngine()

    def resolve_records(
        self,
        records: list[dict[str, Any]],
        *,
        tenant_id: uuid.UUID,
        store: Any | None = None,
    ) -> list[dict[str, Any]]:
        resolved: list[dict[str, Any]] = []
        for rec in records:
            et = str(rec.get("entity_type") or "organization").lower()
            val = str(rec.get("entity_value") or "")
            if not val:
                continue
            er_type = "organization" if et == "Organization" else et.lower()
            result = self._engine.resolve_with_scoring(
                tenant_id=tenant_id,
                entity_type=er_type,
                value=val,
                source=str(rec.get("source_type") or "crif"),
                confidence=float(rec.get("confidence") or 0.5),
                display_name=val,
                store=store,
            )
            resolved.append(
                {
                    "entity_type": rec.get("entity_type"),
                    "entity_value": val,
                    "canonical_key": result.entity.canonical_key,
                    "decision": result.decision.value,
                    "confidence": result.confidence,
                    "entity_id": str(result.entity.id),
                    "explain": result.explain,
                    "source_record": rec,
                }
            )
        return resolved


_resolver: CRIFEntityResolver | None = None


def get_entity_resolver() -> CRIFEntityResolver:
    global _resolver
    if _resolver is None:
        _resolver = CRIFEntityResolver()
    return _resolver
