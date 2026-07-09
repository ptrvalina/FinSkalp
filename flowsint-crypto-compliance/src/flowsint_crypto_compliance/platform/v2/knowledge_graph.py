"""High-level Knowledge Graph service — RFC-0003."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import (
    Entity,
    EntityType,
    Evidence,
    KnowledgeRelation,
    RelationWithoutEvidenceError,
    normalize_entity_type,
)
from flowsint_crypto_compliance.platform.v2.graph_history import GraphHistoryService
from flowsint_crypto_compliance.platform.v2.knowledge_store import KnowledgeGraphStore, get_knowledge_graph_store
from flowsint_crypto_compliance.platform.v2.relation_types import RELATION_TYPE_LABELS_RU, RelationType


def knowledge_model_manifest() -> dict[str, Any]:
    """RFC-0003 manifest for API."""
    entity_types = [
        {"value": et.value, "label_ru": _ENTITY_LABELS_RU.get(et.value, et.value)}
        for et in EntityType
        if et.value not in _DUPLICATE_ALIAS_VALUES
    ]
    relation_types = [
        {"value": rt.value, "label_ru": RELATION_TYPE_LABELS_RU.get(rt.value, rt.value)}
        for rt in RelationType
    ]
    return {
        "rfc": "RFC-0003",
        "schema_version": "3.0.0",
        "title": "Единая модель данных и граф знаний v2.0",
        "entity_types": entity_types,
        "relation_types": relation_types,
        "mandatory_ingest_path": [
            "source",
            "event",
            "normalize",
            "entity_resolution",
            "knowledge_graph",
            "evidence",
            "analytics",
            "investigation",
            "report",
        ],
        "appendix_a_complete": True,
        "rules": {
            "relation_requires_evidence": True,
            "message_ru": "Связь без доказательства не может считаться фактом",
        },
    }


_ENTITY_LABELS_RU: dict[str, str] = {
    "person": "физическое лицо",
    "alias": "псевдоним",
    "username": "имя пользователя",
    "nickname": "никнейм",
    "company": "компания",
    "exchange": "биржа",
    "bank": "банк",
    "gov_agency": "госорган",
    "ngo": "НКО",
    "wallet": "кошелёк",
    "blockchain_address": "блокчейн-адрес",
    "smart_contract": "смарт-контракт",
    "ens_domain": "ENS-домен",
    "dns_domain": "DNS-домен",
    "email": "электронная почта",
    "phone": "телефон",
    "ip_address": "IP-адрес",
    "device_fp": "отпечаток устройства",
    "transaction": "транзакция",
    "asset": "актив",
    "token": "токен",
    "bank_account": "банковский счёт",
    "card": "платёжная карта",
    "passport": "паспорт",
    "contract": "договор",
    "invoice": "счёт-фактура",
    "court_decision": "судебное решение",
    "pdf": "PDF-документ",
    "image": "изображение",
    "ocr_doc": "OCR-документ",
    "telegram": "Telegram",
    "forum": "форум",
    "leak": "утечка",
    "registry": "реестр",
    "explorer": "блокчейн-эксплорер",
    "sanctions": "санкционный список",
    "news": "новости",
    "social": "соцсеть",
    "case": "дело",
    "organization": "организация (legacy)",
    "domain": "домен (legacy)",
    "document": "документ",
    "evidence": "доказательство",
}

# Skip alias values that duplicate canonical entries in manifest
_DUPLICATE_ALIAS_VALUES = {"organization", "domain", "sanction_record", "registry_record"}


class KnowledgeGraphService:
    """Wraps store + history + graph queries."""

    def __init__(
        self,
        *,
        store: KnowledgeGraphStore | None = None,
        history: GraphHistoryService | None = None,
    ) -> None:
        self._store = store or get_knowledge_graph_store()
        self._history = history or GraphHistoryService(store=self._store)

    @property
    def store(self) -> KnowledgeGraphStore:
        return self._store

    def get_entity(self, entity_id: uuid.UUID) -> Entity | None:
        return self._store.get_entity(entity_id)

    def get_neighbors(
        self,
        entity_id: uuid.UUID,
        *,
        direction: str = "both",
        relation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._store.get_neighbors(entity_id, direction=direction, relation_type=relation_type)

    def get_entity_history(self, entity_id: uuid.UUID) -> list[dict[str, Any]]:
        return self._history.get_entity_history(entity_id)

    def get_relation_history(self, relation_id: uuid.UUID) -> list[dict[str, Any]]:
        return self._history.get_relation_history(relation_id)

    def compare_entity_versions(
        self,
        entity_id: uuid.UUID,
        version_a: int,
        version_b: int,
    ) -> dict[str, Any]:
        return self._history.compare_versions(entity_id, version_a, version_b)

    def get_relation_evidence(self, relation_id: uuid.UUID) -> list[Evidence]:
        return self._store.get_relation_evidence(relation_id)

    def graph_at(self, tenant_id: uuid.UUID, as_of: datetime) -> dict[str, Any]:
        return self._history.reconstruct_graph_at(tenant_id, as_of)

    def create_graph_snapshot(
        self,
        tenant_id: uuid.UUID,
        *,
        as_of: datetime | None = None,
        changed_by: str = "api",
    ) -> dict[str, Any]:
        ts = as_of or datetime.now(timezone.utc)
        entities = self._store.list_entities(tenant_id)
        relations = self._store.list_relations(tenant_id)
        snap = self._history.snapshot_at(
            tenant_id=tenant_id,
            as_of=ts,
            entities=entities,
            relations=relations,
        )
        snap["created_by"] = changed_by
        return snap

    def export_evidence_base(
        self,
        tenant_id: uuid.UUID,
        *,
        case_ref: str | None = None,
        case_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        return self._store.export_evidence_base(tenant_id, case_ref=case_ref, case_id=case_id)

    def store_evidence(self, evidence: Evidence) -> Evidence:
        return self._store.store_evidence(evidence)

    def get_evidence(self, evidence_id: uuid.UUID) -> Evidence | None:
        return self._store.get_evidence(evidence_id)

    def link_with_evidence(
        self,
        relation: KnowledgeRelation,
        *,
        require_evidence: bool = True,
    ) -> uuid.UUID:
        return self._store.link_relation(relation, require_evidence=require_evidence)


_kg_service: KnowledgeGraphService | None = None


def get_knowledge_graph_service() -> KnowledgeGraphService:
    global _kg_service
    if _kg_service is None:
        _kg_service = KnowledgeGraphService()
    return _kg_service
