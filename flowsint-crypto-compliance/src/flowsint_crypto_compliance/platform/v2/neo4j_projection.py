"""Unified Neo4j projection — single label map for Wallet/Case (RFC-0002 M2, TD-S2)."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import Entity, EntityType

# Canonical v2 labels — replaces ComplianceWallet / ComplianceCase split schemas.
V2_NEO4J_LABELS: dict[EntityType, str] = {
    EntityType.WALLET: "FinskalpWallet",
    EntityType.BLOCKCHAIN_ADDRESS: "FinskalpWallet",
    EntityType.CASE: "FinskalpCase",
    EntityType.PERSON: "FinskalpPerson",
    EntityType.ALIAS: "FinskalpAlias",
    EntityType.USERNAME: "FinskalpUsername",
    EntityType.NICKNAME: "FinskalpNickname",
    EntityType.COMPANY: "FinskalpCompany",
    EntityType.EXCHANGE: "FinskalpExchange",
    EntityType.BANK: "FinskalpBank",
    EntityType.GOVERNMENT_AGENCY: "FinskalpGovAgency",
    EntityType.NGO: "FinskalpNgo",
    EntityType.ORGANIZATION: "FinskalpOrganization",
    EntityType.SMART_CONTRACT: "FinskalpSmartContract",
    EntityType.ENS_DOMAIN: "FinskalpEnsDomain",
    EntityType.DNS_DOMAIN: "FinskalpDomain",
    EntityType.DOMAIN: "FinskalpDomain",
    EntityType.EMAIL: "FinskalpEmail",
    EntityType.PHONE: "FinskalpPhone",
    EntityType.IP_ADDRESS: "FinskalpIpAddress",
    EntityType.DEVICE_FINGERPRINT: "FinskalpDevice",
    EntityType.TRANSACTION: "FinskalpTransaction",
    EntityType.ASSET: "FinskalpAsset",
    EntityType.TOKEN: "FinskalpToken",
    EntityType.BANK_ACCOUNT: "FinskalpBankAccount",
    EntityType.CARD: "FinskalpCard",
    EntityType.PASSPORT: "FinskalpPassport",
    EntityType.CONTRACT: "FinskalpContract",
    EntityType.INVOICE: "FinskalpInvoice",
    EntityType.COURT_DECISION: "FinskalpCourtDecision",
    EntityType.PDF: "FinskalpDocument",
    EntityType.IMAGE: "FinskalpDocument",
    EntityType.OCR_DOCUMENT: "FinskalpDocument",
    EntityType.DOCUMENT: "FinskalpDocument",
    EntityType.TELEGRAM: "FinskalpTelegram",
    EntityType.FORUM: "FinskalpForum",
    EntityType.LEAK: "FinskalpLeak",
    EntityType.REGISTRY: "FinskalpRegistry",
    EntityType.BLOCKCHAIN_EXPLORER: "FinskalpExplorer",
    EntityType.SANCTIONS_LIST: "FinskalpSanctions",
    EntityType.SANCTION_RECORD: "FinskalpSanctions",
    EntityType.NEWS: "FinskalpNews",
    EntityType.SOCIAL_MEDIA: "FinskalpSocial",
    EntityType.EVIDENCE: "FinskalpEvidence",
    EntityType.REGISTRY_RECORD: "FinskalpRegistry",
}

LEGACY_LABEL_ALIASES: dict[str, str] = {
    "ComplianceWallet": "FinskalpWallet",
    "ComplianceCase": "FinskalpCase",
    "ComplianceSubject": "FinskalpPerson",
    "ComplianceOsintMention": "FinskalpEvidence",
}


def neo4j_label_for(entity_type: EntityType) -> str:
    return V2_NEO4J_LABELS.get(entity_type, "FinskalpEntity")


class Neo4jUnifiedProjection:
    """Project canonical entities to Neo4j with unified labels."""

    def project_entity(self, entity: Entity, *, case_ref: str | None = None) -> dict[str, Any]:
        connection = _get_connection()
        if connection is None:
            return {"projected": False, "reason": "neo4j_unavailable", "entity_id": str(entity.id)}

        label = neo4j_label_for(entity.entity_type)
        try:
            connection.query(
                f"""
                MERGE (n:{label} {{canonical_key: $canonical_key, tenant_id: $tenant_id}})
                SET n.entity_id = $entity_id,
                    n.entity_type = $entity_type,
                    n.display_name = $display_name,
                    n.version = $version,
                    n.updated_at = datetime()
                """,
                {
                    "canonical_key": entity.canonical_key,
                    "tenant_id": str(entity.tenant_id),
                    "entity_id": str(entity.id),
                    "entity_type": entity.entity_type.value,
                    "display_name": entity.display_name,
                    "version": entity.version,
                },
            )
            if case_ref and entity.entity_type == EntityType.CASE:
                connection.query(
                    """
                    MERGE (c:FinskalpCase {case_ref: $case_ref})
                    SET c.canonical_key = $canonical_key,
                        c.entity_id = $entity_id,
                        c.updated_at = datetime()
                    """,
                    {
                        "case_ref": case_ref,
                        "canonical_key": entity.canonical_key,
                        "entity_id": str(entity.id),
                    },
                )
            elif case_ref:
                connection.query(
                    f"""
                    MATCH (c:FinskalpCase {{case_ref: $case_ref}})
                    MATCH (n:{label} {{canonical_key: $canonical_key, tenant_id: $tenant_id}})
                    MERGE (c)-[:HAS_ENTITY]->(n)
                    """,
                    {
                        "case_ref": case_ref,
                        "canonical_key": entity.canonical_key,
                        "tenant_id": str(entity.tenant_id),
                    },
                )
            return {"projected": True, "label": label, "entity_id": str(entity.id)}
        except Exception:
            return {"projected": False, "reason": "neo4j_unavailable", "entity_id": str(entity.id)}

    def project_relation(
        self,
        *,
        from_key: str,
        to_key: str,
        tenant_id: str,
        relation_type: str,
        case_ref: str | None = None,
    ) -> dict[str, Any]:
        connection = _get_connection()
        if connection is None:
            return {"projected": False, "reason": "neo4j_unavailable"}
        try:
            connection.query(
                """
                MATCH (a:FinskalpEntity {canonical_key: $from_key, tenant_id: $tenant_id})
                MATCH (b:FinskalpEntity {canonical_key: $to_key, tenant_id: $tenant_id})
                MERGE (a)-[r:FINSKALP_REL {rel_type: $rel_type}]->(b)
                SET r.case_ref = $case_ref,
                    r.updated_at = datetime()
                """,
                {
                    "from_key": from_key,
                    "to_key": to_key,
                    "tenant_id": tenant_id,
                    "rel_type": relation_type,
                    "case_ref": case_ref,
                },
            )
            return {"projected": True, "relation_type": relation_type}
        except Exception:
            return {"projected": False, "reason": "neo4j_unavailable"}


def _get_connection():
    try:
        from flowsint_crypto_compliance.storage.neo4j_exporter import _get_connection as _conn

        return _conn()
    except Exception:
        return None


def project_evidence_graph(
    graph: Any,
    *,
    case_ref: str,
    investigation_id: str | None = None,
) -> dict[str, Any]:
    """Project fusion evidence graph nodes via unified canonical labels (new writes)."""
    import os
    import uuid

    tenant_raw = os.getenv("FINSKALP_TENANT_ID", "00000000-0000-0000-0000-000000000001")
    tenant_id = uuid.UUID(tenant_raw)
    projection = Neo4jUnifiedProjection()
    results: list[dict[str, Any]] = []
    # EvidenceGraph.nodes may be [] (falsy) — do not fall through to .get on the object
    if hasattr(graph, "nodes") and not isinstance(graph, dict):
        nodes = list(getattr(graph, "nodes") or [])
    elif isinstance(graph, dict):
        nodes = list(graph.get("nodes") or [])
    else:
        nodes = []
    for node in nodes:
        kind = getattr(node, "kind", None)
        kind_val = kind.value if hasattr(kind, "value") else str(getattr(node, "kind", "wallet"))
        if "wallet" not in kind_val.lower() and kind_val not in ("crypto_address", "blockchain_address"):
            continue
        primary = getattr(node, "primary_key", None) or node.get("label") or node.get("id", "")
        chain = "unknown"
        address = str(primary)
        if ":" in address:
            chain, address = address.split(":", 1)
        ent = Entity(
            tenant_id=tenant_id,
            entity_type=EntityType.WALLET,
            canonical_key=f"{chain}:{address}",
            display_name=str(primary),
        )
        results.append(projection.project_entity(ent, case_ref=case_ref))
    return {
        "projected": len(results),
        "case_ref": case_ref,
        "investigation_id": investigation_id,
        "details": results,
    }
