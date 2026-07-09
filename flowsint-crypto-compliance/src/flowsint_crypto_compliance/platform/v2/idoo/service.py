"""RFC-0021 IDOO service facade."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.idoo.backup import backup_manifest
from flowsint_crypto_compliance.platform.v2.idoo.cicd import cicd_manifest
from flowsint_crypto_compliance.platform.v2.idoo.manifest import idoo_manifest
from flowsint_crypto_compliance.platform.v2.idoo.monitoring import get_idoo_metrics
from flowsint_crypto_compliance.platform.v2.idoo.operations import operations_manifest
from flowsint_crypto_compliance.platform.v2.idoo.orchestrator import (
    collect_observability_snapshot,
    get_platform_health,
)
from flowsint_crypto_compliance.platform.v2.idoo.queues import queues_manifest


class IDOOService:
    """Infrastructure, DevOps & Observability service."""

    def manifest(self) -> dict[str, Any]:
        return idoo_manifest()

    def health(self) -> dict[str, Any]:
        return get_platform_health()

    def observability(self) -> dict[str, Any]:
        return collect_observability_snapshot()

    def cicd(self) -> dict[str, Any]:
        return cicd_manifest()

    def runbooks(self) -> dict[str, Any]:
        return operations_manifest()

    def queues(self) -> dict[str, Any]:
        return queues_manifest()

    def backup(self) -> dict[str, Any]:
        return backup_manifest()

    def monitoring_metrics(self) -> dict[str, Any]:
        return {"ok": True, **get_idoo_metrics().get_metrics()}


_service: IDOOService | None = None


def get_idoo_service() -> IDOOService:
    global _service
    if _service is None:
        _service = IDOOService()
    return _service
