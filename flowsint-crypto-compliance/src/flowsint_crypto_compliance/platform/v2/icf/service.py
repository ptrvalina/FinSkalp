"""RFC-0014 ICF service facade."""

from __future__ import annotations

import uuid
from typing import Any

from flowsint_crypto_compliance.platform.v2.icf.manifest import icf_manifest
from flowsint_crypto_compliance.platform.v2.icf.monitoring import get_icf_monitoring
from flowsint_crypto_compliance.platform.v2.icf.orchestrator import run_icf_pipeline
from flowsint_crypto_compliance.platform.v2.icf.scheduler import get_collection_scheduler


class ICFService:
    """Intelligence Collection Framework service."""

    def manifest(self) -> dict[str, Any]:
        return icf_manifest()

    async def collect(
        self,
        *,
        connector_id: str,
        tenant_id: uuid.UUID,
        query: dict[str, Any] | None = None,
        case_ref: str | None = None,
        publish: bool = True,
    ) -> dict[str, Any]:
        result = await run_icf_pipeline(
            connector_id=connector_id,
            tenant_id=tenant_id,
            query=query,
            case_ref=case_ref,
            publish=publish,
        )
        return result.to_dict()

    def scheduler_status(self) -> dict[str, Any]:
        return get_collection_scheduler().status()

    def schedule_job(
        self,
        *,
        connector_id: str,
        query: dict[str, Any] | None = None,
        case_ref: str | None = None,
        tenant_id: str | None = None,
        interval_seconds: int = 300,
    ) -> dict[str, Any]:
        job = get_collection_scheduler().schedule(
            connector_id=connector_id,
            query=query,
            case_ref=case_ref,
            tenant_id=tenant_id,
            interval_seconds=interval_seconds,
        )
        return job.to_dict()

    def monitoring(self, connector_id: str | None = None) -> dict[str, Any]:
        return get_icf_monitoring().get_metrics(connector_id)


_service: ICFService | None = None


def get_icf_service() -> ICFService:
    global _service
    if _service is None:
        _service = ICFService()
    return _service
