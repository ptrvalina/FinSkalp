"""Temporal graph queries — list snapshots in a time window (additive)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any


def list_temporal_snapshots(
    tenant_id: uuid.UUID,
    *,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    from flowsint_crypto_compliance.platform.v2.knowledge_store import get_knowledge_graph_store

    store = get_knowledge_graph_store()
    snapshots: list[dict[str, Any]] = []

    memory_snaps = getattr(store._memory, "graph_snapshots", [])
    for snap in memory_snaps:
        if str(snap.get("tenant_id")) != str(tenant_id):
            continue
        as_of_raw = snap.get("as_of")
        if not as_of_raw:
            continue
        try:
            as_of = datetime.fromisoformat(str(as_of_raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if from_ts and as_of < from_ts:
            continue
        if to_ts and as_of > to_ts:
            continue
        snapshots.append(
            {
                "as_of": as_of_raw,
                "entity_count": snap.get("entity_count", 0),
                "relation_count": snap.get("relation_count", 0),
                "source": "memory",
            }
        )

    if store._can_use_db():
        from flowsint_crypto_compliance.storage.db_models import FinskalpGraphSnapshot

        db = store._db()
        own = store._external_session is None
        try:
            q = db.query(FinskalpGraphSnapshot).filter(FinskalpGraphSnapshot.tenant_id == tenant_id)
            if from_ts:
                q = q.filter(FinskalpGraphSnapshot.as_of >= from_ts)
            if to_ts:
                q = q.filter(FinskalpGraphSnapshot.as_of <= to_ts)
            rows = q.order_by(FinskalpGraphSnapshot.as_of.desc()).limit(limit).all()
            for row in rows:
                snapshots.append(
                    {
                        "as_of": row.as_of.isoformat() if row.as_of else None,
                        "entity_count": (row.snapshot or {}).get("entity_count", 0),
                        "relation_count": (row.snapshot or {}).get("relation_count", 0),
                        "source": "postgres",
                    }
                )
        finally:
            if own:
                db.close()

    snapshots.sort(key=lambda s: s.get("as_of") or "", reverse=True)
    return {
        "ok": True,
        "tenant_id": str(tenant_id),
        "from": from_ts.isoformat() if from_ts else None,
        "to": to_ts.isoformat() if to_ts else None,
        "count": len(snapshots[:limit]),
        "snapshots": snapshots[:limit],
    }
