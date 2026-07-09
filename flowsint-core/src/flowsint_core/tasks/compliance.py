from __future__ import annotations

import uuid
from typing import Any

from celery import states
from sqlalchemy.orm import Session

from flowsint_core.core.celery import celery
from flowsint_core.core.postgre_db import SessionLocal
from flowsint_crypto_compliance.observability.tracing import trace_celery_task
from flowsint_crypto_compliance.services.compliance_service import ComplianceService
from flowsint_types.fiat_crypto import Chain, ControlPurchaseEvent, LicensedPlatformEvent


def _parse_licensed(row: dict[str, Any]) -> LicensedPlatformEvent:
    return LicensedPlatformEvent(
        event_id=str(row["event_id"]),
        platform_name=str(row["platform_name"]),
        platform_license_id=row.get("platform_license_id"),
        region=row.get("region"),
        direction=str(row["direction"]).lower(),
        chain=Chain(str(row["chain"]).lower()),
        address=str(row["address"]),
        amount_crypto=row.get("amount_crypto"),
        asset=row.get("asset"),
        amount_fiat=row.get("amount_fiat"),
        currency=row.get("currency"),
        user_ref=row.get("user_ref"),
        observed_at=row.get("observed_at"),
    )


def _parse_control(row: dict[str, Any]) -> ControlPurchaseEvent:
    return ControlPurchaseEvent(
        event_id=str(row["event_id"]),
        operator_ref=str(row["operator_ref"]),
        region=str(row["region"]),
        channel=str(row["channel"]),
        chain=Chain(str(row["chain"]).lower()),
        source_address=row.get("source_address"),
        target_address=str(row["target_address"]),
        asset=row.get("asset"),
        amount_fiat=row.get("amount_fiat"),
        currency=row.get("currency"),
        observed_at=row.get("observed_at"),
        notes=row.get("notes"),
    )


@celery.task(name="run_compliance_fusion", bind=True)
@trace_celery_task("run_compliance_fusion")
def run_compliance_fusion(
    self,
    case_id: str,
    run_id: str,
    licensed_events: list[dict[str, Any]] | None = None,
    control_purchases: list[dict[str, Any]] | None = None,
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
):
    """Execute OSINT fusion for a compliance case (Celery worker entrypoint)."""
    from flowsint_crypto_compliance.infrastructure.idempotency import IdempotencyStore, make_idempotency_key

    idem = idempotency_key or make_idempotency_key("fusion", case_id, run_id)
    store = IdempotencyStore()
    state = store.acquire("run_compliance_fusion", idem)
    if state == "done":
        cached = store.get_result("run_compliance_fusion", idem)
        if cached is not None:
            return cached

    session: Session = SessionLocal()
    try:
        service = ComplianceService(session)
        run_uuid = uuid.UUID(run_id)
        case_uuid = uuid.UUID(case_id)

        service.update_fusion_run(
            run_uuid,
            status="running",
            celery_task_id=self.request.id,
        )
        session.commit()

        licensed = [_parse_licensed(row) for row in (licensed_events or [])]
        controls = [_parse_control(row) for row in (control_purchases or [])]
        result = service.fuse_case_sync(
            case_uuid,
            licensed_events=licensed,
            control_purchases=controls,
        )

        service.update_fusion_run(run_uuid, status="completed", result=result)
        service.log_audit(
            case_id=case_uuid,
            action="fusion_async_completed",
            payload={"run_id": run_id, "celery_task_id": self.request.id},
            correlation_id=correlation_id or run_id,
        )
        session.commit()
        store.complete("run_compliance_fusion", idem, result)
        return result
    except Exception as exc:
        session.rollback()
        store.release("run_compliance_fusion", idem)
        service = ComplianceService(session)
        service.update_fusion_run(
            uuid.UUID(run_id),
            status="failed",
            error=str(exc)[:2000],
            celery_task_id=self.request.id,
        )
        service.log_audit(
            case_id=uuid.UUID(case_id),
            action="fusion_async_failed",
            payload={"run_id": run_id, "error": str(exc)[:500]},
            correlation_id=run_id,
        )
        session.commit()
        self.update_state(state=states.FAILURE)
        raise
    finally:
        session.close()
