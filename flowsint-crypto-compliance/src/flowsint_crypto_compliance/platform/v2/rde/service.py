"""RFC-0016 RDE service facade."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.rde.manifest import rde_manifest
from flowsint_crypto_compliance.platform.v2.rde.monitoring import get_rde_metrics
from flowsint_crypto_compliance.platform.v2.rde.orchestrator import run_rde_assessment
from flowsint_crypto_compliance.platform.v2.rde.prioritization import prioritize_investigation_objects
from flowsint_crypto_compliance.platform.v2.rde.rules_engine import get_rules_engine
from flowsint_crypto_compliance.platform.v2.rde.temporal import get_temporal_store


class RDEService:
    """Risk & Decision Engine service."""

    def manifest(self) -> dict[str, Any]:
        return rde_manifest()

    async def assess(
        self,
        *,
        entity_key: str,
        tenant_id: uuid.UUID,
        case_ref: str | None = None,
        signals: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = await run_rde_assessment(
            entity_key=entity_key,
            tenant_id=tenant_id,
            case_ref=case_ref,
            signals=signals,
        )
        return result.to_dict()

    def get_rules(self) -> dict[str, Any]:
        engine = get_rules_engine()
        return {"ok": True, "rules": engine.list_rules(), "history": engine.get_history()}

    def evaluate_rules(self, context: dict[str, Any]) -> dict[str, Any]:
        engine = get_rules_engine()
        events = engine.evaluate(context)
        if events:
            get_rde_metrics().rule_events_fired += len(events)
        return {
            "ok": True,
            "events": [e.to_dict() for e in events],
            "event_count": len(events),
        }

    def monitoring(self) -> dict[str, Any]:
        return {"ok": True, **get_rde_metrics().get_metrics()}

    def priorities(self, case_ref: str | None = None) -> dict[str, Any]:
        store = get_temporal_store()
        all_priorities: list[dict[str, Any]] = []
        for entity_key in store._snapshots:
            snaps = store.get_snapshots(entity_key)
            if not snaps:
                continue
            latest = snaps[-1]
            if case_ref and latest.case_ref and latest.case_ref != case_ref:
                continue
            items = prioritize_investigation_objects(
                entity_key=entity_key,
                case_ref=case_ref or latest.case_ref,
                factor_scores=latest.factor_scores,
                correlations=[],
                rule_events=[],
                composite_score=latest.composite_score,
            )
            all_priorities.extend(items)
        all_priorities.sort(key=lambda p: p.get("priority_score", 0), reverse=True)
        return {"ok": True, "case_ref": case_ref, "priorities": all_priorities, "count": len(all_priorities)}


_service: RDEService | None = None


def get_rde_service() -> RDEService:
    global _service
    if _service is None:
        _service = RDEService()
    return _service
