"""Postgres-backed entity label store + bootstrap sync metadata."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.attribution.entity_label_store import EntityLabelStore
from flowsint_crypto_compliance.attribution.types import EntityLabel


def entity_store_mode() -> str:
    from flowsint_crypto_compliance.platform.v2.entity_store_mode import entity_store_mode as _mode

    return _mode()


def _session():
    from flowsint_core.core.postgre_db import SessionLocal

    return SessionLocal()


class PostgresEntityLabelStore(EntityLabelStore):
    """In-memory cache backed by compliance_entity_labels."""

    def __init__(self) -> None:
        super().__init__()
        self._load_from_db()

    def _load_from_db(self) -> None:
        try:
            from flowsint_crypto_compliance.storage.db_models import ComplianceEntityLabel
        except Exception:
            return
        db = _session()
        try:
            rows = db.query(ComplianceEntityLabel).all()
            for row in rows:
                lbl = _row_to_label(row)
                self._labels[self._key(lbl.chain, lbl.address)] = lbl
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "Could not load entity labels from Postgres: %s", exc
            )
            raise
        finally:
            db.close()

    def upsert(self, label: EntityLabel, *, force: bool = False) -> bool:
        changed = super().upsert(label, force=force)
        if changed:
            self._persist_row(label)
            try:
                from flowsint_crypto_compliance.platform.v2.entity_label_bridge import sync_entity_label_to_kg

                sync_entity_label_to_kg(label)
            except Exception:
                pass
        return changed

    def _persist_row(self, label: EntityLabel) -> None:
        try:
            from flowsint_crypto_compliance.storage.db_models import ComplianceEntityLabel
            from sqlalchemy.dialects.postgresql import insert
        except Exception:
            return
        db = _session()
        try:
            addr = label.address.lower() if label.chain == "eth" else label.address
            stmt = (
                insert(ComplianceEntityLabel)
                .values(
                    chain=label.chain,
                    address=addr,
                    label=label.label,
                    category=label.category,
                    confidence=label.confidence,
                    source=label.source,
                    tier=label.tier,
                    risk_score=label.risk_score,
                    sanctioned=label.sanctioned,
                    cluster_ref=label.cluster_ref,
                    evidence=label.evidence,
                    status=getattr(label, "status", "active"),
                    reviewed_by=getattr(label, "reviewed_by", None),
                    reviewed_at=getattr(label, "reviewed_at", None),
                    added_at=label.added_at or datetime.now(timezone.utc),
                )
                .on_conflict_do_update(
                    index_elements=["chain", "address"],
                    set_={
                        "label": label.label,
                        "category": label.category,
                        "confidence": label.confidence,
                        "source": label.source,
                        "tier": label.tier,
                        "risk_score": label.risk_score,
                        "sanctioned": label.sanctioned,
                        "cluster_ref": label.cluster_ref,
                        "evidence": label.evidence,
                        "status": getattr(label, "status", "active"),
                        "reviewed_by": getattr(label, "reviewed_by", None),
                        "reviewed_at": getattr(label, "reviewed_at", None),
                    },
                )
            )
            db.execute(stmt)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def lookup(self, chain: str, address: str) -> EntityLabel | None:
        lbl = super().lookup(chain, address)
        if lbl and lbl.rejected:
            return None
        return lbl


def _row_to_label(row: Any) -> EntityLabel:
    return EntityLabel(
        address=row.address,
        chain=row.chain,
        label=row.label,
        category=row.category or "unknown",
        confidence=float(row.confidence or 0.5),
        source=row.source,
        tier=int(row.tier or 2),
        risk_score=float(row.risk_score or 0),
        sanctioned=bool(row.sanctioned),
        cluster_ref=row.cluster_ref,
        evidence=row.evidence,
        added_at=row.added_at or datetime.now(timezone.utc),
        status=getattr(row, "status", None) or "active",
        reviewed_by=getattr(row, "reviewed_by", None),
        reviewed_at=getattr(row, "reviewed_at", None),
    )


_SYNC_KEY = "open_datasets_bootstrap"


def should_skip_bootstrap() -> bool:
    if entity_store_mode() != "postgres" or not os.getenv("DATABASE_URL"):
        return False
    try:
        from flowsint_crypto_compliance.storage.db_models import ComplianceAttributionSyncState
    except Exception:
        return False
    db = _session()
    try:
        row = (
            db.query(ComplianceAttributionSyncState)
            .filter(ComplianceAttributionSyncState.sync_key == _SYNC_KEY)
            .one_or_none()
        )
        return row is not None
    except Exception:
        return False
    finally:
        db.close()


def record_bootstrap(stats: dict[str, Any]) -> None:
    if entity_store_mode() != "postgres" or not os.getenv("DATABASE_URL"):
        return
    try:
        from flowsint_crypto_compliance.storage.db_models import ComplianceAttributionSyncState
    except Exception:
        return
    db = _session()
    try:
        row = (
            db.query(ComplianceAttributionSyncState)
            .filter(ComplianceAttributionSyncState.sync_key == _SYNC_KEY)
            .one_or_none()
        )
        now = datetime.now(timezone.utc)
        payload = json.dumps(stats, default=str)[:8000]
        if row:
            row.last_sync_at = now
            row.stats_json = payload
        else:
            db.add(
                ComplianceAttributionSyncState(
                    sync_key=_SYNC_KEY,
                    last_sync_at=now,
                    stats_json=payload,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def analyst_confirm_label(
    *,
    chain: str,
    address: str,
    label: str,
    category: str,
    analyst_id: str,
) -> EntityLabel:
    from flowsint_crypto_compliance.attribution.entity_label_store import get_entity_label_store
    from flowsint_crypto_compliance.attribution.types import TIER_ANALYST_CONFIRMED

    now = datetime.now(timezone.utc)
    el = EntityLabel(
        address=address,
        chain=chain,
        label=label,
        category=category,
        confidence=1.0,
        source="analyst_confirmed",
        tier=TIER_ANALYST_CONFIRMED,
        risk_score=10.0,
        status="confirmed",
        reviewed_by=analyst_id,
        reviewed_at=now,
        evidence=f"analyst_confirmed:{analyst_id}",
    )
    store = get_entity_label_store()
    store.upsert(el, force=True)
    return el


def analyst_reject_label(
    *,
    chain: str,
    address: str,
    label: str,
    category: str,
    analyst_id: str,
) -> EntityLabel:
    from flowsint_crypto_compliance.attribution.entity_label_store import get_entity_label_store

    now = datetime.now(timezone.utc)
    el = EntityLabel(
        address=address,
        chain=chain,
        label=label,
        category=category,
        confidence=0.0,
        source="analyst_rejected",
        tier=3,
        risk_score=0.0,
        status="rejected",
        reviewed_by=analyst_id,
        reviewed_at=now,
        evidence=f"analyst_rejected:{analyst_id}",
    )
    store = get_entity_label_store()
    store.upsert(el, force=True)
    return el
