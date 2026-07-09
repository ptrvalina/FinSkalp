"""RFC-0019 Ch.5 — GraphQL stub schema + manifest."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.aspp.versioning import PLATFORM_API_VERSION

GRAPHQL_SCHEMA_STUB = """
type Query {
  investigationDashboard(caseRef: String!): InvestigationDashboard
  platformManifest: PlatformManifest
  pluginCatalog(category: String): [Plugin!]!
}

type InvestigationDashboard {
  caseRef: String!
  evidenceCount: Int!
  riskLevel: String
  timelineEvents: [TimelineEvent!]!
  openQuestions: [String!]!
}

type TimelineEvent {
  id: ID!
  eventType: String!
  occurredAt: String!
  summaryRu: String
}

type PlatformManifest {
  rfc: String!
  schemaVersion: String!
  titleRu: String!
}

type Plugin {
  pluginId: ID!
  category: String!
  version: String!
  healthStatus: String!
}
""".strip()


def graphql_manifest() -> dict[str, Any]:
    return {
        "rfc": "RFC-0019",
        "chapter": 5,
        "schema_version": PLATFORM_API_VERSION,
        "status": "stub",
        "read_only": True,
        "endpoint_stub": "/api/platform/v2/aspp/graphql",
        "schema_sdl": GRAPHQL_SCHEMA_STUB,
        "queries": [
            "investigationDashboard",
            "platformManifest",
            "pluginCatalog",
        ],
        "mutations": [],
        "subscriptions": [],
        "principle_ru": "GraphQL — read-only запросы для дашборда расследования (stub)",
        "technical_debt": "TD-ASPP-1",
    }
