"""Knowledge Graph Store — Postgres + in-memory persistence (RFC-0002 M2, RFC-0003)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import (
    Entity,
    EntityAttribute,
    EntityType,
    Evidence,
    KnowledgeRelation,
    RelationWithoutEvidenceError,
    normalize_entity_type,
)


def _session():
    from flowsint_core.core.postgre_db import SessionLocal

    return SessionLocal()


class _InMemoryBackend:
    """Fallback store for tests and offline mode."""

    def __init__(self) -> None:
        self.entities: dict[uuid.UUID, Entity] = {}
        self.entities_by_key: dict[tuple[uuid.UUID, str, str], uuid.UUID] = {}
        self.relations: dict[uuid.UUID, KnowledgeRelation] = {}
        self.evidence: dict[uuid.UUID, Evidence] = {}
        self.entity_versions: dict[uuid.UUID, list[dict[str, Any]]] = {}
        self.relation_versions: dict[uuid.UUID, list[dict[str, Any]]] = {}
        self.graph_snapshots: list[dict[str, Any]] = []

    def upsert_entity(self, entity: Entity) -> Entity:
        key = (entity.tenant_id, entity.entity_type.value, entity.canonical_key)
        existing_id = self.entities_by_key.get(key)
        if existing_id and existing_id in self.entities:
            existing = self.entities[existing_id]
            entity = entity.model_copy(
                update={
                    "id": existing_id,
                    "version": max(existing.version, entity.version),
                    "display_name": entity.display_name or existing.display_name,
                }
            )
        self.entities[entity.id] = entity
        self.entities_by_key[key] = entity.id
        return entity

    def link_relation(self, relation: KnowledgeRelation, *, require_evidence: bool = True) -> uuid.UUID:
        if require_evidence and not relation.evidence_ids:
            raise RelationWithoutEvidenceError()
        self.relations[relation.id] = relation
        return relation.id

    def store_evidence(self, evidence: Evidence) -> Evidence:
        if evidence.id in self.evidence:
            self.evidence[evidence.id] = evidence
            return evidence
        for ev in self.evidence.values():
            if ev.tenant_id == evidence.tenant_id and ev.content_hash == evidence.content_hash:
                return evidence.model_copy(update={"id": ev.id})
        self.evidence[evidence.id] = evidence
        return evidence


_kg_store: KnowledgeGraphStore | None = None


def _kg_use_memory(*, use_memory: bool = False) -> bool:
    """Resolve store backend: explicit use_memory=True, else FINSKALP_ENTITY_STORE (default postgres)."""
    if use_memory:
        return True
    raw = os.getenv("FINSKALP_ENTITY_STORE", "postgres").strip().lower()
    return raw in ("memory", "in_memory")


def get_knowledge_graph_store(*, use_memory: bool = False) -> KnowledgeGraphStore:
    global _kg_store
    if _kg_store is None:
        _kg_store = KnowledgeGraphStore(use_memory=_kg_use_memory(use_memory=use_memory))
    return _kg_store


class KnowledgeGraphStore:
    """Upsert canonical entities, relations, and evidence."""

    def __init__(self, session: Any | None = None, *, use_memory: bool = False) -> None:
        self._external_session = session
        self._memory = _InMemoryBackend()
        self._force_memory = use_memory
        self._db_available: bool | None = None

    def _db(self):
        return self._external_session or _session()

    def _can_use_db(self) -> bool:
        if self._force_memory:
            return False
        if self._db_available is False:
            return False
        try:
            _session()
            self._db_available = True
            return True
        except Exception:
            self._db_available = False
            return False

    def upsert_entity(self, entity: Entity) -> Entity:
        if not self._can_use_db():
            stored = self._memory.upsert_entity(entity)
            self.record_entity_version(stored)
            return stored

        from flowsint_crypto_compliance.storage.db_models import (
            FinskalpEntity,
            FinskalpEntityAttribute,
        )

        own = self._external_session is None
        db = self._db()
        try:
            row = (
                db.query(FinskalpEntity)
                .filter(
                    FinskalpEntity.tenant_id == entity.tenant_id,
                    FinskalpEntity.entity_type == entity.entity_type.value,
                    FinskalpEntity.canonical_key == entity.canonical_key,
                )
                .first()
            )
            if row:
                row.display_name = entity.display_name or row.display_name
                row.version = max(row.version, entity.version)
                entity = entity.model_copy(update={"id": row.id, "version": row.version})
            else:
                row = FinskalpEntity(
                    id=entity.id,
                    tenant_id=entity.tenant_id,
                    entity_type=entity.entity_type.value,
                    canonical_key=entity.canonical_key,
                    display_name=entity.display_name,
                    version=entity.version,
                )
                db.add(row)
                db.flush()
                entity = entity.model_copy(update={"id": row.id})

            for attr in entity.attributes:
                db.add(
                    FinskalpEntityAttribute(
                        entity_id=entity.id,
                        key=attr.key,
                        value={"v": attr.value},
                        source=attr.source,
                        confidence=attr.confidence,
                        valid_from=attr.valid_from,
                    )
                )
            if own:
                db.commit()
            stored = self._memory.upsert_entity(entity)
            self.record_entity_version(stored)
            return stored
        except Exception:
            if own:
                db.rollback()
            stored = self._memory.upsert_entity(entity)
            self.record_entity_version(stored)
            return stored
        finally:
            if own:
                db.close()

    def link_relation(
        self,
        relation_or_from: KnowledgeRelation | uuid.UUID | str,
        to_id: uuid.UUID | str | None = None,
        relation_type: str | None = None,
        *,
        tenant_id: uuid.UUID | None = None,
        confidence: float = 0.5,
        evidence_ids: list[uuid.UUID] | None = None,
        require_evidence: bool = True,
        source: str = "unknown",
        acquisition_method: str = "inferred",
        actor: str = "system",
        valid_until: datetime | None = None,
    ) -> uuid.UUID:
        """Link entities — RFC-0003 requires evidence for facts."""
        if isinstance(relation_or_from, KnowledgeRelation):
            relation = relation_or_from
        else:
            if to_id is None or relation_type is None or tenant_id is None:
                raise ValueError("to_id, relation_type, tenant_id required for legacy link_relation call")
            relation = KnowledgeRelation(
                tenant_id=tenant_id,
                from_entity_id=uuid.UUID(str(relation_or_from)),
                to_entity_id=uuid.UUID(str(to_id)),
                relation_type=relation_type,
                confidence=confidence,
                evidence_ids=list(evidence_ids or []),
                source=source,
                acquisition_method=acquisition_method,
                actor=actor,
                valid_until=valid_until,
            )

        if require_evidence and not relation.evidence_ids:
            raise RelationWithoutEvidenceError()

        if not self._can_use_db():
            rel_id = self._memory.link_relation(relation, require_evidence=require_evidence)
            self.record_relation_version(relation)
            return rel_id

        from flowsint_crypto_compliance.storage.db_models import FinskalpEntityRelation

        own = self._external_session is None
        db = self._db()
        try:
            db.add(
                FinskalpEntityRelation(
                    id=relation.id,
                    tenant_id=relation.tenant_id,
                    from_entity_id=relation.from_entity_id,
                    to_entity_id=relation.to_entity_id,
                    relation_type=relation.relation_type,
                    confidence=relation.confidence,
                    evidence_ids=[str(e) for e in relation.evidence_ids],
                    source=relation.source,
                    acquisition_method=relation.acquisition_method,
                    actor=relation.actor,
                    valid_until=relation.valid_until,
                    version=relation.version,
                    history=relation.history,
                )
            )
            if own:
                db.commit()
            self._memory.link_relation(relation, require_evidence=False)
            self.record_relation_version(relation)
            return relation.id
        except Exception:
            if own:
                db.rollback()
            rel_id = self._memory.link_relation(relation, require_evidence=False)
            self.record_relation_version(relation)
            return rel_id
        finally:
            if own:
                db.close()

    def store_evidence(self, evidence: Evidence) -> Evidence:
        if not self._can_use_db():
            return self._memory.store_evidence(evidence)

        from flowsint_crypto_compliance.storage.db_models import FinskalpEvidence

        own = self._external_session is None
        db = self._db()
        try:
            existing = (
                db.query(FinskalpEvidence)
                .filter(
                    FinskalpEvidence.tenant_id == evidence.tenant_id,
                    FinskalpEvidence.content_hash == evidence.content_hash,
                )
                .first()
            )
            if existing:
                if existing.id == evidence.id:
                    existing.payload = evidence.payload
                    if own:
                        db.commit()
                    return evidence.model_copy(update={"id": existing.id})
                return evidence.model_copy(update={"id": existing.id})
            db.add(
                FinskalpEvidence(
                    id=evidence.id,
                    tenant_id=evidence.tenant_id,
                    case_id=evidence.case_id,
                    entity_id=evidence.entity_id,
                    source_type=evidence.source_type,
                    content_hash=evidence.content_hash,
                    snapshot_uri=evidence.snapshot_uri,
                    trust_level=evidence.trust_level,
                    payload=evidence.payload,
                    discovered_at=evidence.discovered_at,
                    acquisition_method=evidence.acquisition_method,
                    digital_signature=evidence.digital_signature,
                    original_uri=evidence.original_uri,
                    retention_policy=evidence.retention_policy,
                    valid_until=evidence.valid_until,
                )
            )
            if own:
                db.commit()
            return self._memory.store_evidence(evidence)
        except Exception:
            if own:
                db.rollback()
            return self._memory.store_evidence(evidence)
        finally:
            if own:
                db.close()

    def get_evidence(self, evidence_id: uuid.UUID) -> Evidence | None:
        if evidence_id in self._memory.evidence:
            return self._memory.evidence[evidence_id]
        if not self._can_use_db():
            return None
        from flowsint_crypto_compliance.storage.db_models import FinskalpEvidence

        own = self._external_session is None
        db = self._db()
        try:
            from flowsint_crypto_compliance.platform.v2.canonical import TrustLevel

            row = db.query(FinskalpEvidence).filter(FinskalpEvidence.id == evidence_id).first()
            if not row:
                return None
            return Evidence(
                id=row.id,
                tenant_id=row.tenant_id,
                case_id=row.case_id,
                entity_id=row.entity_id,
                source_type=row.source_type,
                content_hash=row.content_hash,
                snapshot_uri=row.snapshot_uri,
                discovered_at=row.discovered_at,
                trust=TrustLevel(
                    source_reliability=float(row.trust_level or 0.5),
                    information_credibility=float(row.trust_level or 0.5),
                ),
                payload=row.payload or {},
                acquisition_method=row.acquisition_method or "automated_collection",
                digital_signature=row.digital_signature,
                original_uri=row.original_uri,
                retention_policy=row.retention_policy or "standard_7y",
                valid_until=row.valid_until,
            )
        except Exception:
            return None
        finally:
            if own:
                db.close()

    def get_entity(self, entity_id: uuid.UUID) -> Entity | None:
        if entity_id in self._memory.entities:
            return self._memory.entities[entity_id]
        if not self._can_use_db():
            return None
        from flowsint_crypto_compliance.storage.db_models import FinskalpEntity

        own = self._external_session is None
        db = self._db()
        try:
            row = db.query(FinskalpEntity).filter(FinskalpEntity.id == entity_id).first()
            if not row:
                return None
            return Entity(
                id=row.id,
                tenant_id=row.tenant_id,
                entity_type=normalize_entity_type(row.entity_type),
                canonical_key=row.canonical_key,
                display_name=row.display_name,
                version=row.version,
            )
        finally:
            if own:
                db.close()

    def get_entity_by_key(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_type: str,
        canonical_key: str,
    ) -> Entity | None:
        key = (tenant_id, entity_type, canonical_key)
        mem_id = self._memory.entities_by_key.get(key)
        if mem_id:
            return self._memory.entities.get(mem_id)

        if not self._can_use_db():
            return None

        from flowsint_crypto_compliance.storage.db_models import FinskalpEntity

        own = self._external_session is None
        db = self._db()
        try:
            row = (
                db.query(FinskalpEntity)
                .filter(
                    FinskalpEntity.tenant_id == tenant_id,
                    FinskalpEntity.entity_type == entity_type,
                    FinskalpEntity.canonical_key == canonical_key,
                )
                .first()
            )
            if not row:
                return None
            return Entity(
                id=row.id,
                tenant_id=row.tenant_id,
                entity_type=normalize_entity_type(row.entity_type),
                canonical_key=row.canonical_key,
                display_name=row.display_name,
                version=row.version,
            )
        finally:
            if own:
                db.close()

    def search_entities_by_value(self, tenant_id: uuid.UUID, value: str) -> list[Entity]:
        needle = value.strip().lower()
        hits = [
            e
            for e in self._memory.entities.values()
            if e.tenant_id == tenant_id
            and (needle in e.canonical_key.lower() or needle in e.display_name.lower())
        ]
        return hits

    def get_neighbors(
        self,
        entity_id: uuid.UUID,
        *,
        direction: str = "both",
        relation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        neighbors: list[dict[str, Any]] = []
        for rel in self._memory.relations.values():
            if relation_type and rel.relation_type != relation_type:
                continue
            if direction in ("out", "both") and rel.from_entity_id == entity_id:
                other = self.get_entity(rel.to_entity_id)
                neighbors.append(
                    {
                        "direction": "out",
                        "relation_id": str(rel.id),
                        "relation_type": rel.relation_type,
                        "confidence": rel.confidence,
                        "entity": other.model_dump(mode="json") if other else None,
                    }
                )
            if direction in ("in", "both") and rel.to_entity_id == entity_id:
                other = self.get_entity(rel.from_entity_id)
                neighbors.append(
                    {
                        "direction": "in",
                        "relation_id": str(rel.id),
                        "relation_type": rel.relation_type,
                        "confidence": rel.confidence,
                        "entity": other.model_dump(mode="json") if other else None,
                    }
                )

        if self._can_use_db():
            from flowsint_crypto_compliance.storage.db_models import FinskalpEntityRelation

            own = self._external_session is None
            db = self._db()
            try:
                q = db.query(FinskalpEntityRelation)
                if direction == "out":
                    q = q.filter(FinskalpEntityRelation.from_entity_id == entity_id)
                elif direction == "in":
                    q = q.filter(FinskalpEntityRelation.to_entity_id == entity_id)
                else:
                    q = q.filter(
                        (FinskalpEntityRelation.from_entity_id == entity_id)
                        | (FinskalpEntityRelation.to_entity_id == entity_id)
                    )
                if relation_type:
                    q = q.filter(FinskalpEntityRelation.relation_type == relation_type)
                for row in q.all():
                    other_id = row.to_entity_id if row.from_entity_id == entity_id else row.from_entity_id
                    other = self.get_entity(other_id)
                    dir_val = "out" if row.from_entity_id == entity_id else "in"
                    entry = {
                        "direction": dir_val,
                        "relation_id": str(row.id),
                        "relation_type": row.relation_type,
                        "confidence": row.confidence,
                        "entity": other.model_dump(mode="json") if other else None,
                    }
                    if entry not in neighbors:
                        neighbors.append(entry)
            finally:
                if own:
                    db.close()
        return neighbors

    def get_relation_evidence(self, relation_id: uuid.UUID) -> list[Evidence]:
        rel = self._memory.relations.get(relation_id)
        evidence_ids: list[uuid.UUID] = []
        if rel:
            evidence_ids = rel.evidence_ids
        elif self._can_use_db():
            from flowsint_crypto_compliance.storage.db_models import FinskalpEntityRelation

            own = self._external_session is None
            db = self._db()
            try:
                row = db.query(FinskalpEntityRelation).filter(FinskalpEntityRelation.id == relation_id).first()
                if row and row.evidence_ids:
                    evidence_ids = [uuid.UUID(str(e)) for e in row.evidence_ids]
            finally:
                if own:
                    db.close()

        out: list[Evidence] = []
        for eid in evidence_ids:
            if eid in self._memory.evidence:
                out.append(self._memory.evidence[eid])
        return out

    def record_entity_version(
        self,
        entity: Entity,
        *,
        changed_by: str = "system",
        changed_at: datetime | None = None,
    ) -> int:
        ts = changed_at or datetime.now(timezone.utc)
        entry = {
            "version": entity.version,
            "snapshot": entity.model_dump(mode="json"),
            "changed_by": changed_by,
            "changed_at": ts.isoformat(),
        }
        self._memory.entity_versions.setdefault(entity.id, []).append(entry)

        if self._can_use_db():
            from flowsint_crypto_compliance.storage.db_models import FinskalpEntityVersion

            own = self._external_session is None
            db = self._db()
            try:
                db.add(
                    FinskalpEntityVersion(
                        entity_id=entity.id,
                        version=entity.version,
                        snapshot=entry["snapshot"],
                        changed_by=changed_by,
                        changed_at=ts,
                    )
                )
                if own:
                    db.commit()
            except Exception:
                if own:
                    db.rollback()
            finally:
                if own:
                    db.close()
        return entity.version

    def record_relation_version(
        self,
        relation: KnowledgeRelation,
        *,
        changed_by: str = "system",
        changed_at: datetime | None = None,
    ) -> int:
        ts = changed_at or datetime.now(timezone.utc)
        entry = {
            "version": relation.version,
            "snapshot": relation.model_dump(mode="json"),
            "changed_by": changed_by,
            "changed_at": ts.isoformat(),
        }
        self._memory.relation_versions.setdefault(relation.id, []).append(entry)

        if self._can_use_db():
            from flowsint_crypto_compliance.storage.db_models import FinskalpRelationVersion

            own = self._external_session is None
            db = self._db()
            try:
                db.add(
                    FinskalpRelationVersion(
                        relation_id=relation.id,
                        version=relation.version,
                        snapshot=entry["snapshot"],
                        changed_by=changed_by,
                        changed_at=ts,
                    )
                )
                if own:
                    db.commit()
            except Exception:
                if own:
                    db.rollback()
            finally:
                if own:
                    db.close()
        return relation.version

    def get_entity_at_version(self, entity_id: uuid.UUID, version: int) -> Entity | None:
        for entry in reversed(self._memory.entity_versions.get(entity_id, [])):
            if entry["version"] == version:
                return Entity.model_validate(entry["snapshot"])
        if self._can_use_db():
            from flowsint_crypto_compliance.storage.db_models import FinskalpEntityVersion

            own = self._external_session is None
            db = self._db()
            try:
                row = (
                    db.query(FinskalpEntityVersion)
                    .filter(
                        FinskalpEntityVersion.entity_id == entity_id,
                        FinskalpEntityVersion.version == version,
                    )
                    .first()
                )
                if row:
                    return Entity.model_validate(row.snapshot)
            finally:
                if own:
                    db.close()
        return None

    def get_entity_history(self, entity_id: uuid.UUID) -> list[dict[str, Any]]:
        mem = self._memory.entity_versions.get(entity_id, [])
        if mem or not self._can_use_db():
            return mem
        from flowsint_crypto_compliance.storage.db_models import FinskalpEntityVersion

        own = self._external_session is None
        db = self._db()
        try:
            rows = (
                db.query(FinskalpEntityVersion)
                .filter(FinskalpEntityVersion.entity_id == entity_id)
                .order_by(FinskalpEntityVersion.version)
                .all()
            )
            return [
                {
                    "version": r.version,
                    "snapshot": r.snapshot,
                    "changed_by": r.changed_by,
                    "changed_at": r.changed_at.isoformat() if r.changed_at else None,
                }
                for r in rows
            ]
        finally:
            if own:
                db.close()

    def get_relation_history(self, relation_id: uuid.UUID) -> list[dict[str, Any]]:
        mem = self._memory.relation_versions.get(relation_id, [])
        if mem or not self._can_use_db():
            return mem
        from flowsint_crypto_compliance.storage.db_models import FinskalpRelationVersion

        own = self._external_session is None
        db = self._db()
        try:
            rows = (
                db.query(FinskalpRelationVersion)
                .filter(FinskalpRelationVersion.relation_id == relation_id)
                .order_by(FinskalpRelationVersion.version)
                .all()
            )
            return [
                {
                    "version": r.version,
                    "snapshot": r.snapshot,
                    "changed_by": r.changed_by,
                    "changed_at": r.changed_at.isoformat() if r.changed_at else None,
                }
                for r in rows
            ]
        finally:
            if own:
                db.close()

    def store_graph_snapshot(
        self,
        *,
        tenant_id: uuid.UUID,
        as_of: datetime,
        snapshot: dict[str, Any],
    ) -> None:
        self._memory.graph_snapshots.append(snapshot)
        if self._can_use_db():
            from flowsint_crypto_compliance.storage.db_models import FinskalpGraphSnapshot

            own = self._external_session is None
            db = self._db()
            try:
                db.add(
                    FinskalpGraphSnapshot(
                        tenant_id=tenant_id,
                        as_of=as_of,
                        snapshot=snapshot,
                    )
                )
                if own:
                    db.commit()
            except Exception:
                if own:
                    db.rollback()
            finally:
                if own:
                    db.close()

    def get_graph_snapshot(self, tenant_id: uuid.UUID, as_of: datetime) -> dict[str, Any] | None:
        target = as_of.isoformat()
        for snap in reversed(self._memory.graph_snapshots):
            if snap.get("tenant_id") == str(tenant_id) and snap.get("as_of", "") <= target:
                return snap
        if not self._can_use_db():
            return None
        from flowsint_crypto_compliance.storage.db_models import FinskalpGraphSnapshot

        own = self._external_session is None
        db = self._db()
        try:
            row = (
                db.query(FinskalpGraphSnapshot)
                .filter(
                    FinskalpGraphSnapshot.tenant_id == tenant_id,
                    FinskalpGraphSnapshot.as_of <= as_of,
                )
                .order_by(FinskalpGraphSnapshot.as_of.desc())
                .first()
            )
            return row.snapshot if row else None
        finally:
            if own:
                db.close()

    def list_entities(self, tenant_id: uuid.UUID) -> list[Entity]:
        mem = [e for e in self._memory.entities.values() if e.tenant_id == tenant_id]
        if mem or not self._can_use_db():
            return mem
        from flowsint_crypto_compliance.storage.db_models import FinskalpEntity

        own = self._external_session is None
        db = self._db()
        try:
            rows = db.query(FinskalpEntity).filter(FinskalpEntity.tenant_id == tenant_id).all()
            return [
                Entity(
                    id=r.id,
                    tenant_id=r.tenant_id,
                    entity_type=normalize_entity_type(r.entity_type),
                    canonical_key=r.canonical_key,
                    display_name=r.display_name,
                    version=r.version,
                )
                for r in rows
            ]
        finally:
            if own:
                db.close()

    def list_relations(self, tenant_id: uuid.UUID) -> list[KnowledgeRelation]:
        mem = [r for r in self._memory.relations.values() if r.tenant_id == tenant_id]
        if mem or not self._can_use_db():
            return mem
        from flowsint_crypto_compliance.storage.db_models import FinskalpEntityRelation

        own = self._external_session is None
        db = self._db()
        try:
            rows = db.query(FinskalpEntityRelation).filter(FinskalpEntityRelation.tenant_id == tenant_id).all()
            out: list[KnowledgeRelation] = []
            for r in rows:
                out.append(
                    KnowledgeRelation(
                        id=r.id,
                        tenant_id=r.tenant_id,
                        from_entity_id=r.from_entity_id,
                        to_entity_id=r.to_entity_id,
                        relation_type=r.relation_type,
                        confidence=r.confidence,
                        evidence_ids=[uuid.UUID(str(e)) for e in (r.evidence_ids or [])],
                        source=r.source,
                        acquisition_method=r.acquisition_method,
                        actor=r.actor,
                        valid_until=r.valid_until,
                        version=r.version,
                        history=r.history or [],
                    )
                )
            return out
        finally:
            if own:
                db.close()

    def _entity_versions_before(self, tenant_id: uuid.UUID, as_of: datetime) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        tenant_entities = {e.id for e in self.list_entities(tenant_id)}
        for eid in tenant_entities:
            entries.extend(self.get_entity_history(eid))
        if self._can_use_db():
            from flowsint_crypto_compliance.storage.db_models import FinskalpEntity, FinskalpEntityVersion

            own = self._external_session is None
            db = self._db()
            try:
                rows = (
                    db.query(FinskalpEntityVersion)
                    .join(FinskalpEntity, FinskalpEntity.id == FinskalpEntityVersion.entity_id)
                    .filter(
                        FinskalpEntity.tenant_id == tenant_id,
                        FinskalpEntityVersion.changed_at <= as_of,
                    )
                    .order_by(FinskalpEntityVersion.entity_id, FinskalpEntityVersion.version)
                    .all()
                )
                for r in rows:
                    entries.append(
                        {
                            "entity_id": str(r.entity_id),
                            "version": r.version,
                            "snapshot": r.snapshot,
                            "changed_by": r.changed_by,
                            "changed_at": r.changed_at.isoformat() if r.changed_at else None,
                        }
                    )
            finally:
                if own:
                    db.close()
        return [e for e in entries if (e.get("changed_at") or "") <= as_of.isoformat()]

    def _relation_versions_before(self, tenant_id: uuid.UUID, as_of: datetime) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for rel in self.list_relations(tenant_id):
            entries.extend(self.get_relation_history(rel.id))
        if self._can_use_db():
            from flowsint_crypto_compliance.storage.db_models import (
                FinskalpEntityRelation,
                FinskalpRelationVersion,
            )

            own = self._external_session is None
            db = self._db()
            try:
                rows = (
                    db.query(FinskalpRelationVersion)
                    .join(
                        FinskalpEntityRelation,
                        FinskalpEntityRelation.id == FinskalpRelationVersion.relation_id,
                    )
                    .filter(
                        FinskalpEntityRelation.tenant_id == tenant_id,
                        FinskalpRelationVersion.changed_at <= as_of,
                    )
                    .order_by(FinskalpRelationVersion.relation_id, FinskalpRelationVersion.version)
                    .all()
                )
                for r in rows:
                    entries.append(
                        {
                            "relation_id": str(r.relation_id),
                            "version": r.version,
                            "snapshot": r.snapshot,
                            "changed_by": r.changed_by,
                            "changed_at": r.changed_at.isoformat() if r.changed_at else None,
                        }
                    )
            finally:
                if own:
                    db.close()
        return [e for e in entries if (e.get("changed_at") or "") <= as_of.isoformat()]

    def reconstruct_graph_at(self, tenant_id: uuid.UUID, as_of: datetime) -> dict[str, Any]:
        """Rebuild graph state from version history (RFC-0003 Ch.6)."""
        snap = self.get_graph_snapshot(tenant_id, as_of)
        if snap:
            return {**snap, "source": "snapshot", "reconstruction": "stored_snapshot"}

        entity_by_id: dict[uuid.UUID, Entity] = {}
        for entry in self._entity_versions_before(tenant_id, as_of):
            eid_raw = entry.get("entity_id") or (entry.get("snapshot") or {}).get("id")
            if not eid_raw:
                continue
            eid = uuid.UUID(str(eid_raw))
            snap_data = entry.get("snapshot") or {}
            try:
                ent = Entity.model_validate(snap_data)
            except Exception:
                continue
            prev = entity_by_id.get(eid)
            if not prev or ent.version >= prev.version:
                entity_by_id[eid] = ent

        relation_by_id: dict[uuid.UUID, KnowledgeRelation] = {}
        for entry in self._relation_versions_before(tenant_id, as_of):
            rid_raw = entry.get("relation_id") or (entry.get("snapshot") or {}).get("id")
            if not rid_raw:
                continue
            rid = uuid.UUID(str(rid_raw))
            snap_data = entry.get("snapshot") or {}
            try:
                rel = KnowledgeRelation.model_validate(snap_data)
            except Exception:
                continue
            prev = relation_by_id.get(rid)
            if not prev or rel.version >= prev.version:
                relation_by_id[rid] = rel

        # Supplement from platform events (entity_id hints in payload)
        event_entities = self._entities_from_platform_events(tenant_id, as_of)
        for eid, ent in event_entities.items():
            if eid not in entity_by_id:
                entity_by_id[eid] = ent

        entities = list(entity_by_id.values())
        relations = list(relation_by_id.values())
        return {
            "tenant_id": str(tenant_id),
            "as_of": as_of.isoformat(),
            "entity_count": len(entities),
            "relation_count": len(relations),
            "entities": [e.model_dump(mode="json") for e in entities],
            "relations": [r.model_dump(mode="json") for r in relations],
            "source": "reconstructed",
            "reconstruction": "entity_relation_versions_and_events",
        }

    def _entities_from_platform_events(
        self, tenant_id: uuid.UUID, as_of: datetime
    ) -> dict[uuid.UUID, Entity]:
        out: dict[uuid.UUID, Entity] = {}
        if not self._can_use_db():
            return out
        from flowsint_crypto_compliance.storage.db_models import FinskalpPlatformEvent

        own = self._external_session is None
        db = self._db()
        try:
            rows = (
                db.query(FinskalpPlatformEvent)
                .filter(
                    FinskalpPlatformEvent.tenant_id == tenant_id,
                    FinskalpPlatformEvent.occurred_at <= as_of,
                )
                .order_by(FinskalpPlatformEvent.occurred_at)
                .limit(5000)
                .all()
            )
            for row in rows:
                p = row.payload or {}
                eid_raw = p.get("entity_id")
                if not eid_raw:
                    continue
                try:
                    eid = uuid.UUID(str(eid_raw))
                except ValueError:
                    continue
                ent = self.get_entity(eid)
                if ent:
                    out[eid] = ent
        except Exception:
            pass
        finally:
            if own:
                db.close()
        return out

    def export_evidence_base(
        self,
        tenant_id: uuid.UUID,
        *,
        case_ref: str | None = None,
        case_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Export evidence + relations for tenant/case (RFC-0003 Ch.9)."""
        evidence_rows: list[dict[str, Any]] = []
        relations_rows: list[dict[str, Any]] = []

        for ev in self._memory.evidence.values():
            if ev.tenant_id != tenant_id:
                continue
            if case_id and ev.case_id != case_id:
                continue
            if case_ref and (ev.payload or {}).get("case_ref") != case_ref:
                continue
            evidence_rows.append(ev.model_dump(mode="json"))

        for rel in self.list_relations(tenant_id):
            relations_rows.append(rel.model_dump(mode="json"))

        if self._can_use_db():
            from flowsint_crypto_compliance.storage.db_models import FinskalpEvidence

            own = self._external_session is None
            db = self._db()
            try:
                q = db.query(FinskalpEvidence).filter(FinskalpEvidence.tenant_id == tenant_id)
                if case_id:
                    q = q.filter(FinskalpEvidence.case_id == case_id)
                for row in q.all():
                    payload = row.payload or {}
                    if case_ref and payload.get("case_ref") != case_ref and case_ref not in str(payload):
                        if payload.get("case_ref") and payload.get("case_ref") != case_ref:
                            continue
                    evidence_rows.append(
                        {
                            "id": str(row.id),
                            "tenant_id": str(row.tenant_id),
                            "case_id": str(row.case_id) if row.case_id else None,
                            "entity_id": str(row.entity_id) if row.entity_id else None,
                            "source_type": row.source_type,
                            "content_hash": row.content_hash,
                            "trust_level": row.trust_level,
                            "payload": payload,
                            "discovered_at": row.discovered_at.isoformat() if row.discovered_at else None,
                            "acquisition_method": row.acquisition_method,
                            "original_uri": row.original_uri,
                            "retention_policy": row.retention_policy,
                        }
                    )
            finally:
                if own:
                    db.close()

        return {
            "tenant_id": str(tenant_id),
            "case_ref": case_ref,
            "case_id": str(case_id) if case_id else None,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "evidence_count": len(evidence_rows),
            "relation_count": len(relations_rows),
            "evidence": evidence_rows,
            "relations": relations_rows,
        }
