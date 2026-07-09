"""RFC-0022 EGPR service facade."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.egpr.adr_registry import adr_registry_manifest, list_adrs
from flowsint_crypto_compliance.platform.v2.egpr.kpi_maturity import kpi_maturity_manifest
from flowsint_crypto_compliance.platform.v2.egpr.manifest import egpr_manifest
from flowsint_crypto_compliance.platform.v2.egpr.orchestrator import evaluate_maturity
from flowsint_crypto_compliance.platform.v2.egpr.roadmap import roadmap_manifest
from flowsint_crypto_compliance.platform.v2.egpr.rfc_lifecycle import get_rfc_catalog, propose_rfc_transition
from flowsint_crypto_compliance.platform.v2.egpr.tech_debt import tech_debt_manifest


class EGPRService:
    """Enterprise Governance & Product Roadmap service."""

    def manifest(self) -> dict[str, Any]:
        return egpr_manifest()

    def roadmap(self) -> dict[str, Any]:
        return roadmap_manifest()

    def rfc_catalog(self) -> dict[str, Any]:
        catalog = get_rfc_catalog()
        return {"ok": True, "count": len(catalog), "catalog": catalog}

    def adr_list(self) -> dict[str, Any]:
        manifest = adr_registry_manifest()
        return {"ok": True, **manifest, "adrs": list_adrs()}

    def maturity(self) -> dict[str, Any]:
        return evaluate_maturity()

    def tech_debt(self) -> dict[str, Any]:
        return tech_debt_manifest()

    def kpi(self) -> dict[str, Any]:
        return kpi_maturity_manifest()

    def transition_rfc(self, rfc_id: str, target_stage: str, reviewer: str = "architecture_board") -> dict[str, Any]:
        return propose_rfc_transition(rfc_id, target_stage, reviewer=reviewer)


_service: EGPRService | None = None


def get_egpr_service() -> EGPRService:
    global _service
    if _service is None:
        _service = EGPRService()
    return _service
