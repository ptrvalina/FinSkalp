"""RFC-0022 Ch.4 — Architecture Decision Record registry."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.egpr.types import ArchitectureDecisionRecord

_SAMPLE_ADRS: list[ArchitectureDecisionRecord] = [
    ArchitectureDecisionRecord(
        id="ADR-0001",
        date="2026-03-15",
        title="Entity-first knowledge model with Postgres as system of record",
        context=(
            "Platform had fragmented Case/Investigation entities and in-memory graph. "
            "Need unified entity model for compliance and investigation workflows."
        ),
        options=[
            "Keep fragmented models with sync layer",
            "Unified canonical model in Postgres with Neo4j projection",
            "Graph-only with Postgres as cache",
        ],
        decision="Unified canonical model in Postgres with Neo4j projection",
        rationale=(
            "Postgres provides ACID, audit trail, and sovereign deployment. "
            "Neo4j projection enables graph analytics without sacrificing entity integrity."
        ),
        consequences=[
            "Mandatory ingest pipeline required",
            "Entity versioning and temporal replay enabled",
            "Migration path from legacy Investigation/ComplianceCase",
        ],
        related_rfc="RFC-0002",
    ),
    ArchitectureDecisionRecord(
        id="ADR-0002",
        date="2026-05-20",
        title="Harmonized RBAC layer across investigation and compliance",
        context=(
            "Two parallel RBAC systems caused permission drift between "
            "investigation workspace and compliance API."
        ),
        options=[
            "Keep separate role systems with mapping table",
            "Unified enterprise RBAC with domain scopes",
            "External IAM only (Keycloak)",
        ],
        decision="Unified enterprise RBAC with domain scopes",
        rationale=(
            "Single permission model reduces security drift and simplifies "
            "audit. Domain scopes preserve investigation vs compliance separation."
        ),
        consequences=[
            "require_permission on all mutate routes",
            "Effective permissions API for UI",
            "Migration of legacy role names",
        ],
        related_rfc="RFC-0009",
    ),
    ArchitectureDecisionRecord(
        id="ADR-0003",
        date="2026-07-01",
        title="API, SDK & Plugin Platform as extension layer",
        context=(
            "External integrators and internal teams need stable APIs, "
            "multi-language SDKs, and plugin registration without core changes."
        ),
        options=[
            "REST-only with OpenAPI",
            "Full ASPP: REST + events + GraphQL + gRPC + SDKs + marketplace",
            "gRPC-only internal, REST external",
        ],
        decision="Full ASPP: REST + events + GraphQL + gRPC + SDKs + marketplace",
        rationale=(
            "API First and Plugin First principles require comprehensive "
            "developer experience. Event catalog enables event-driven integrations."
        ),
        consequences=[
            "Developer portal and sandbox",
            "Webhook delivery with retry",
            "Plugin registry with manifest validation",
            "4-language SDK stubs (Python, TypeScript, Go, Java)",
        ],
        related_rfc="RFC-0019",
    ),
]

_adr_store: dict[str, ArchitectureDecisionRecord] = {a.id: a for a in _SAMPLE_ADRS}


def list_adrs() -> list[dict[str, Any]]:
    return [a.to_dict() for a in _adr_store.values()]


def get_adr(adr_id: str) -> dict[str, Any] | None:
    record = _adr_store.get(adr_id)
    return record.to_dict() if record else None


def adr_registry_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0022",
        "chapter": 4,
        "store": "in_memory",
        "count": len(_adr_store),
        "adrs": list_adrs(),
        "principle_ru": "ADR — формализованные архитектурные решения с контекстом и последствиями",
    }
