"""Persist analyst graph camera views — Postgres when available, else in-memory."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

_mem: dict[str, list[dict[str, Any]]] = {}


def _session():
    from flowsint_core.core.postgre_db import SessionLocal

    return SessionLocal()


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "investigation_id": str(row.investigation_id),
        "name": row.name,
        "zoom": row.zoom,
        "center": row.center or {"x": 0, "y": 0},
        "expanded_clusters": row.expanded_clusters or [],
        "timeline_ts": row.timeline_ts,
        "pins": row.pins or {},
        "view_mode": row.view_mode or "cluster",
        "highlighted_path": row.highlighted_path,
        "saved_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_views(investigation_id: str) -> list[dict[str, Any]]:
    try:
        from flowsint_crypto_compliance.storage.db_models import ComplianceGraphView

        db = _session()
        try:
            rows = (
                db.query(ComplianceGraphView)
                .filter(ComplianceGraphView.investigation_id == uuid.UUID(investigation_id))
                .order_by(ComplianceGraphView.created_at.desc())
                .limit(24)
                .all()
            )
            if rows:
                return [_row_to_dict(r) for r in rows]
        finally:
            db.close()
    except Exception:
        pass
    return list(_mem.get(investigation_id, []))


def save_view(investigation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("name required")
    entry = {
        "id": payload.get("id") or str(uuid.uuid4()),
        "investigation_id": investigation_id,
        "name": name,
        "zoom": float(payload.get("zoom") or 1.0),
        "center": payload.get("center") or {"x": 0, "y": 0},
        "expanded_clusters": list(payload.get("expanded_clusters") or []),
        "timeline_ts": payload.get("timeline_ts"),
        "pins": dict(payload.get("pins") or {}),
        "view_mode": payload.get("view_mode") or "cluster",
        "highlighted_path": payload.get("highlighted_path"),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        from flowsint_crypto_compliance.storage.db_models import ComplianceGraphView

        inv_uuid = uuid.UUID(investigation_id)
        db = _session()
        try:
            existing = (
                db.query(ComplianceGraphView)
                .filter(
                    ComplianceGraphView.investigation_id == inv_uuid,
                    ComplianceGraphView.name == name,
                )
                .first()
            )
            if existing:
                existing.zoom = entry["zoom"]
                existing.center = entry["center"]
                existing.expanded_clusters = entry["expanded_clusters"]
                existing.timeline_ts = entry["timeline_ts"]
                existing.pins = entry["pins"]
                existing.view_mode = entry["view_mode"]
                existing.highlighted_path = entry["highlighted_path"]
                db.commit()
                db.refresh(existing)
                return _row_to_dict(existing)
            row = ComplianceGraphView(
                id=uuid.UUID(entry["id"]),
                investigation_id=inv_uuid,
                name=name,
                zoom=entry["zoom"],
                center=entry["center"],
                expanded_clusters=entry["expanded_clusters"],
                timeline_ts=entry["timeline_ts"],
                pins=entry["pins"],
                view_mode=entry["view_mode"],
                highlighted_path=entry["highlighted_path"],
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _row_to_dict(row)
        finally:
            db.close()
    except Exception:
        views = _mem.setdefault(investigation_id, [])
        idx = next((i for i, v in enumerate(views) if v.get("name") == name), -1)
        if idx >= 0:
            views[idx] = entry
        else:
            views.append(entry)
        _mem[investigation_id] = views[-24:]
        return entry


def delete_view(investigation_id: str, view_id: str) -> bool:
    try:
        from flowsint_crypto_compliance.storage.db_models import ComplianceGraphView

        db = _session()
        try:
            row = (
                db.query(ComplianceGraphView)
                .filter(
                    ComplianceGraphView.investigation_id == uuid.UUID(investigation_id),
                    ComplianceGraphView.id == uuid.UUID(view_id),
                )
                .first()
            )
            if row:
                db.delete(row)
                db.commit()
                return True
        finally:
            db.close()
    except Exception:
        pass
    views = _mem.get(investigation_id, [])
    before = len(views)
    _mem[investigation_id] = [v for v in views if v.get("id") != view_id and v.get("name") != view_id]
    return len(_mem[investigation_id]) < before
