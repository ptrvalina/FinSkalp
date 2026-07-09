"""Platform event bus — v2 envelope over ComplianceEventBus (RFC-0002)."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

from flowsint_crypto_compliance.infrastructure.compliance_events import get_event_bus
from flowsint_crypto_compliance.platform.v2.events import PlatformEvent

V2_STREAM_KEY = "finskalp:events:v2"


class PlatformEventBus:
    """Publish canonical PlatformEvent; bridge to legacy bus for UI compatibility."""

    def publish(self, event: PlatformEvent) -> dict[str, Any]:
        body = event.model_dump(mode="json")
        legacy = get_event_bus().publish(
            event.legacy_type(),
            payload={
                **event.payload,
                "v2_event_type": event.event_type.value,
                "v2_event_id": str(event.id),
                "investigation_id": str(event.investigation_id) if event.investigation_id else None,
                "tenant_id": str(event.tenant_id) if event.tenant_id else None,
                "source": event.source,
            },
            severity=_severity_for(event),
            correlation_id=event.correlation_id or str(event.id),
            text_ru=_text_ru_for(event),
        )
        self._persist_v2(body)
        self._persist_postgres(event)
        self._dispatch_subscribers(event)
        return {"v2": body, "legacy": legacy}

    def _persist_v2(self, body: dict[str, Any]) -> None:
        url = os.getenv("REDIS_URL")
        if not url:
            return
        try:
            import redis

            client = redis.from_url(url, decode_responses=True)
            client.xadd(
                V2_STREAM_KEY,
                {"json": json.dumps(body, ensure_ascii=False)},
                maxlen=50_000,
                approximate=True,
            )
        except Exception:
            pass

    def _persist_postgres(self, event: PlatformEvent) -> None:
        try:
            from flowsint_core.core.postgre_db import SessionLocal
            from flowsint_crypto_compliance.storage.db_models import FinskalpPlatformEvent

            db = SessionLocal()
            try:
                db.add(
                    FinskalpPlatformEvent(
                        id=event.id,
                        event_type=event.event_type.value,
                        schema_version=event.schema_version,
                        occurred_at=event.occurred_at,
                        source=event.source,
                        actor=event.actor,
                        investigation_id=event.investigation_id,
                        tenant_id=event.tenant_id,
                        correlation_id=event.correlation_id,
                        payload=event.payload,
                    )
                )
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
        except Exception:
            pass

    def _dispatch_subscribers(self, event: PlatformEvent) -> None:
        try:
            from flowsint_crypto_compliance.platform.v2.event_subscriber import get_platform_event_subscriber

            get_platform_event_subscriber().dispatch(event)
        except Exception:
            pass


def _severity_for(event: PlatformEvent) -> str:
    if event.event_type.value in ("SanctionHitDetected", "PatternDetected"):
        return "high"
    if event.event_type.value.endswith("Failed"):
        return "critical"
    return "info"


def _text_ru_for(event: PlatformEvent) -> str:
    p = event.payload
    et = event.event_type.value
    templates = {
        "CaseOpened": f"Дело открыто · {p.get('case_ref', '—')}",
        "EvidenceCreated": f"Доказательство · {p.get('content_hash', '')[:12]}…",
        "FusedIntelligenceReady": f"Fusion готов · {p.get('case_ref', '—')}",
        "RiskUpdated": f"Риск обновлён · {p.get('score', '—')}",
        "EntityMerged": f"Сущности объединены · {len(p.get('merged_ids', []))}",
    }
    return templates.get(et, et)


_bus: PlatformEventBus | None = None


def get_platform_event_bus() -> PlatformEventBus:
    global _bus
    if _bus is None:
        _bus = PlatformEventBus()
    return _bus
