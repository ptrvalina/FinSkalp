"""RFC-0022 EGPR v2.0 manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.events import SCHEMA_VERSION
from flowsint_crypto_compliance.platform.v2.egpr.adr_registry import adr_registry_manifest
from flowsint_crypto_compliance.platform.v2.egpr.architecture_board import board_workflow_manifest
from flowsint_crypto_compliance.platform.v2.egpr.constraints import constraints_manifest
from flowsint_crypto_compliance.platform.v2.egpr.dev_standards import dev_standards_manifest
from flowsint_crypto_compliance.platform.v2.egpr.evolution import evolution_manifest
from flowsint_crypto_compliance.platform.v2.egpr.knowledge import knowledge_manifest
from flowsint_crypto_compliance.platform.v2.egpr.kpi_maturity import kpi_maturity_manifest
from flowsint_crypto_compliance.platform.v2.egpr.maturity import maturity_manifest
from flowsint_crypto_compliance.platform.v2.egpr.mission import mission_manifest
from flowsint_crypto_compliance.platform.v2.egpr.principles import principles_manifest
from flowsint_crypto_compliance.platform.v2.egpr.project_risks import project_risks_manifest
from flowsint_crypto_compliance.platform.v2.egpr.quality import quality_manifest
from flowsint_crypto_compliance.platform.v2.egpr.releases import releases_manifest
from flowsint_crypto_compliance.platform.v2.egpr.requirements import requirements_manifest
from flowsint_crypto_compliance.platform.v2.egpr.roadmap import roadmap_manifest
from flowsint_crypto_compliance.platform.v2.egpr.rfc_lifecycle import rfc_lifecycle_manifest
from flowsint_crypto_compliance.platform.v2.egpr.support import support_manifest
from flowsint_crypto_compliance.platform.v2.egpr.teams import teams_manifest
from flowsint_crypto_compliance.platform.v2.egpr.tech_debt import tech_debt_manifest
from flowsint_crypto_compliance.platform.v2.egpr.types import RoadmapPhase, StrategicPrinciple, TeamDomain
from flowsint_crypto_compliance.platform.v2.egpr.vision import vision_manifest


def egpr_manifest() -> dict[str, Any]:
    mission = mission_manifest()
    return {
        "rfc": "RFC-0022",
        "schema_version": SCHEMA_VERSION,
        "title": "Enterprise Governance & Product Roadmap v2.0",
        "title_ru": "Корпоративное управление и дорожная карта продукта v2.0",
        "principle": "Governed Evolution",
        "principle_ru": "Управляемая эволюция архитектуры через RFC, ADR и Architecture Board",
        "chapters": list(range(1, 21)),
        "volume_i_status": "complete",
        "volume_i_badge_ru": "Volume I Complete",
        "strategic_principles": [p.value for p in StrategicPrinciple],
        "roadmap_phases": [p.value for p in RoadmapPhase],
        "team_domains": [d.value for d in TeamDomain],
        "mission": mission,
        "principles": principles_manifest(),
        "architecture_board": board_workflow_manifest(),
        "adr_registry": adr_registry_manifest(),
        "rfc_lifecycle": rfc_lifecycle_manifest(),
        "releases": releases_manifest(),
        "dev_standards": dev_standards_manifest(),
        "tech_debt": tech_debt_manifest(),
        "requirements": requirements_manifest(),
        "quality": quality_manifest(),
        "knowledge": knowledge_manifest(),
        "project_risks": project_risks_manifest(),
        "teams": teams_manifest(),
        "kpi_maturity": kpi_maturity_manifest(),
        "roadmap": roadmap_manifest(),
        "maturity": maturity_manifest(),
        "support": support_manifest(),
        "evolution": evolution_manifest(),
        "vision": vision_manifest(),
        "constraints": constraints_manifest(),
        "api": {
            "manifest": "/api/platform/v2/egpr/manifest",
            "roadmap": "/api/platform/v2/egpr/roadmap",
            "rfc_catalog": "/api/platform/v2/egpr/rfc-catalog",
            "adr": "/api/platform/v2/egpr/adr",
            "maturity": "/api/platform/v2/egpr/maturity",
            "tech_debt": "/api/platform/v2/egpr/tech-debt",
            "kpi": "/api/platform/v2/egpr/kpi",
            "rfc_transition": "/api/platform/v2/egpr/rfc/{rfc_id}/transition",
        },
    }
