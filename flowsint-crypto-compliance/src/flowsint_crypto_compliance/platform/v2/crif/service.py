"""RFC-0015 CRIF service facade."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.crif.change_history import get_change_history_store
from flowsint_crypto_compliance.platform.v2.crif.manifest import crif_manifest
from flowsint_crypto_compliance.platform.v2.crif.metrics import get_crif_metrics
from flowsint_crypto_compliance.platform.v2.crif.orchestrator import run_crif_pipeline
from flowsint_crypto_compliance.platform.v2.crif.rules_engine import get_rules_engine
from flowsint_crypto_compliance.platform.v2.crif.sanctions import screen_sanctions


class CRIFService:
    """Compliance & Registry Intelligence Framework service."""

    def manifest(self) -> dict[str, Any]:
        return crif_manifest()

    async def check(
        self,
        *,
        connector_id: str,
        tenant_id: uuid.UUID,
        query: dict[str, Any] | None = None,
        case_ref: str | None = None,
        organization_key: str | None = None,
        publish: bool = True,
    ) -> dict[str, Any]:
        result = await run_crif_pipeline(
            connector_id=connector_id,
            tenant_id=tenant_id,
            query=query,
            case_ref=case_ref,
            organization_key=organization_key,
            publish=publish,
        )
        return result.to_dict()

    def screen_sanctions(self, name: str) -> dict[str, Any]:
        get_crif_metrics().record_sanctions_screen()
        matches = screen_sanctions(name)
        return {
            "ok": True,
            "query": name,
            "matches": matches,
            "match_count": len(matches),
            "requires_analyst": any(m.get("requires_analyst_confirmation") for m in matches),
        }

    def get_rules(self) -> dict[str, Any]:
        return {"ok": True, "rules": get_rules_engine().list_rules()}

    def evaluate_rules(self, context: dict[str, Any]) -> dict[str, Any]:
        events = get_rules_engine().evaluate(context)
        if events:
            get_crif_metrics().record_rules_fired("rules_engine", len(events))
        return {
            "ok": True,
            "events": [e.to_dict() for e in events],
            "event_count": len(events),
        }

    def metrics(self, connector_id: str | None = None) -> dict[str, Any]:
        return {"ok": True, **get_crif_metrics().get_metrics(connector_id)}

    def change_history(self, entity_key: str) -> dict[str, Any]:
        timeline = get_change_history_store().get_timeline(entity_key)
        return {
            "ok": True,
            "entity_key": entity_key,
            "timeline": timeline,
            "count": len(timeline),
        }


_service: CRIFService | None = None


def get_crif_service() -> CRIFService:
    global _service
    if _service is None:
        _service = CRIFService()
    return _service
