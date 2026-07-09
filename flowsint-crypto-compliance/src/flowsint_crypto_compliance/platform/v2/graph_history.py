"""Graph history — entity/relation versioning and temporal snapshots (RFC-0003 Ch.6)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.canonical import Entity, KnowledgeRelation


class GraphHistoryService:
    """Version tracking and point-in-time graph queries."""

    def __init__(self, store: Any | None = None) -> None:
        self._store = store
        self._entity_versions: dict[uuid.UUID, list[dict[str, Any]]] = {}
        self._relation_versions: dict[uuid.UUID, list[dict[str, Any]]] = {}
        self._snapshots: list[dict[str, Any]] = []

    def record_entity_version(
        self,
        entity: Entity,
        *,
        changed_by: str = "system",
        changed_at: datetime | None = None,
    ) -> int:
        ts = changed_at or datetime.now(timezone.utc)
        snapshot = entity.model_dump(mode="json")
        entry = {
            "version": entity.version,
            "snapshot": snapshot,
            "changed_by": changed_by,
            "changed_at": ts.isoformat(),
        }
        self._entity_versions.setdefault(entity.id, []).append(entry)
        if self._store and hasattr(self._store, "record_entity_version"):
            self._store.record_entity_version(entity, changed_by=changed_by, changed_at=ts)
        return entity.version

    def record_relation_version(
        self,
        relation: KnowledgeRelation,
        *,
        changed_by: str = "system",
        changed_at: datetime | None = None,
    ) -> int:
        ts = changed_at or datetime.now(timezone.utc)
        snapshot = relation.model_dump(mode="json")
        entry = {
            "version": relation.version,
            "snapshot": snapshot,
            "changed_by": changed_by,
            "changed_at": ts.isoformat(),
        }
        self._relation_versions.setdefault(relation.id, []).append(entry)
        if self._store and hasattr(self._store, "record_relation_version"):
            self._store.record_relation_version(relation, changed_by=changed_by, changed_at=ts)
        return relation.version

    def get_entity_at_version(self, entity_id: uuid.UUID, version: int) -> Entity | None:
        if self._store and hasattr(self._store, "get_entity_at_version"):
            stored = self._store.get_entity_at_version(entity_id, version)
            if stored:
                return stored
        versions = self._entity_versions.get(entity_id, [])
        for entry in reversed(versions):
            if entry["version"] == version:
                return Entity.model_validate(entry["snapshot"])
        return None

    def get_entity_history(self, entity_id: uuid.UUID) -> list[dict[str, Any]]:
        if self._store and hasattr(self._store, "get_entity_history"):
            return self._store.get_entity_history(entity_id)
        return list(self._entity_versions.get(entity_id, []))

    def get_relation_history(self, relation_id: uuid.UUID) -> list[dict[str, Any]]:
        if self._store and hasattr(self._store, "get_relation_history"):
            return self._store.get_relation_history(relation_id)
        return list(self._relation_versions.get(relation_id, []))

    def compare_versions(
        self,
        entity_id: uuid.UUID,
        version_a: int,
        version_b: int,
    ) -> dict[str, Any]:
        a = self.get_entity_at_version(entity_id, version_a)
        b = self.get_entity_at_version(entity_id, version_b)
        if not a or not b:
            return {"error": "Версия не найдена", "entity_id": str(entity_id)}
        attrs_a = {x.key: x.value for x in a.attributes}
        attrs_b = {x.key: x.value for x in b.attributes}
        added = {k: attrs_b[k] for k in attrs_b if k not in attrs_a}
        removed = {k: attrs_a[k] for k in attrs_a if k not in attrs_b}
        changed = {
            k: {"from": attrs_a[k], "to": attrs_b[k]}
            for k in attrs_a
            if k in attrs_b and attrs_a[k] != attrs_b[k]
        }
        return {
            "entity_id": str(entity_id),
            "version_a": version_a,
            "version_b": version_b,
            "display_name_changed": a.display_name != b.display_name,
            "added_attributes": added,
            "removed_attributes": removed,
            "changed_attributes": changed,
        }

    def snapshot_at(
        self,
        *,
        tenant_id: uuid.UUID,
        as_of: datetime,
        entities: list[Entity],
        relations: list[KnowledgeRelation],
    ) -> dict[str, Any]:
        """Capture graph state at a point in time."""
        snap = {
            "tenant_id": str(tenant_id),
            "as_of": as_of.isoformat(),
            "entity_count": len(entities),
            "relation_count": len(relations),
            "entities": [e.model_dump(mode="json") for e in entities],
            "relations": [r.model_dump(mode="json") for r in relations],
        }
        self._snapshots.append(snap)
        if self._store and hasattr(self._store, "store_graph_snapshot"):
            self._store.store_graph_snapshot(tenant_id=tenant_id, as_of=as_of, snapshot=snap)
        return snap

    def get_snapshot_at(self, tenant_id: uuid.UUID, as_of: datetime) -> dict[str, Any] | None:
        if self._store and hasattr(self._store, "get_graph_snapshot"):
            stored = self._store.get_graph_snapshot(tenant_id, as_of)
            if stored:
                return stored
        target = as_of.isoformat()
        candidates = [s for s in self._snapshots if s["tenant_id"] == str(tenant_id)]
        if not candidates:
            return None
        candidates.sort(key=lambda s: s["as_of"], reverse=True)
        for snap in candidates:
            if snap["as_of"] <= target:
                return snap
        return candidates[-1] if candidates else None

    def reconstruct_graph_at(self, tenant_id: uuid.UUID, as_of: datetime) -> dict[str, Any]:
        """Point-in-time graph via snapshot or version replay (RFC-0003 Ch.6)."""
        snap = self.get_snapshot_at(tenant_id, as_of)
        if snap:
            return {**snap, "source": "snapshot", "reconstruction": "stored_snapshot"}
        if self._store and hasattr(self._store, "reconstruct_graph_at"):
            return self._store.reconstruct_graph_at(tenant_id, as_of)
        return {
            "tenant_id": str(tenant_id),
            "as_of": as_of.isoformat(),
            "entity_count": 0,
            "relation_count": 0,
            "entities": [],
            "relations": [],
            "source": "empty",
            "reconstruction": "none",
        }
