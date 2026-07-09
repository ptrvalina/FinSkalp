"""RFC-0013 — distributed lock for per-chain block sync."""

from __future__ import annotations

import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator

_memory_locks: dict[str, threading.Lock] = {}
_memory_holders: dict[str, str] = {}
_holder_local = threading.local()

LOCK_TTL_SECONDS = int(os.getenv("FINSKALP_SYNC_LOCK_TTL", "300"))


def _lock_name(chain: str) -> str:
    return f"block_sync:{chain.lower()}"


def _holder_id() -> str:
    holder = getattr(_holder_local, "holder_id", None)
    if holder is None:
        holder = os.getenv("FINSKALP_WORKER_ID", str(uuid.uuid4()))
        _holder_local.holder_id = holder
    return holder


@contextmanager
def chain_sync_lock(chain: str, *, use_memory: bool | None = None) -> Iterator[bool]:
    """Acquire per-chain sync lock. Yields True if acquired."""
    memory = use_memory if use_memory is not None else os.getenv("FINSKALP_ENTITY_STORE", "").lower() in (
        "memory",
        "in_memory",
    )
    name = _lock_name(chain)
    if memory:
        acquired = _acquire_memory_lock(name)
        try:
            yield acquired
        finally:
            if acquired:
                _release_memory_lock(name)
        return

    acquired = False
    try:
        from flowsint_core.core.postgre_db import SessionLocal

        db = SessionLocal()
        try:
            acquired = _acquire_postgres_lock(db, name)
            yield acquired
            if acquired:
                db.commit()
            else:
                db.rollback()
        finally:
            if acquired:
                _release_postgres_lock(db, name)
                db.commit()
            db.close()
    except Exception:
        acquired = _acquire_memory_lock(name)
        try:
            yield acquired
        finally:
            if acquired:
                _release_memory_lock(name)


def _acquire_memory_lock(name: str) -> bool:
    lock = _memory_locks.setdefault(name, threading.Lock())
    if not lock.acquire(blocking=False):
        return False
    _memory_holders[name] = _holder_id()
    return True


def _release_memory_lock(name: str) -> None:
    lock = _memory_locks.get(name)
    if lock and lock.locked():
        lock.release()
    _memory_holders.pop(name, None)


def _acquire_postgres_lock(db, name: str) -> bool:
    from sqlalchemy import text

    from flowsint_crypto_compliance.storage.db_models import FinskalpSyncLock

    # Try Postgres advisory lock first
    try:
        row = db.execute(text("SELECT pg_try_advisory_lock(hashtext(:k))"), {"k": name}).scalar()
        if row:
            return True
    except Exception:
        db.rollback()

    # Fallback: row-level lease lock
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=LOCK_TTL_SECONDS)
    holder = _holder_id()
    existing = db.get(FinskalpSyncLock, name)
    if existing and existing.expires_at > now and existing.holder_id != holder:
        return False
    if existing:
        existing.holder_id = holder
        existing.acquired_at = now
        existing.expires_at = expires
    else:
        db.add(FinskalpSyncLock(lock_name=name, holder_id=holder, expires_at=expires))
    db.flush()
    return True


def _release_postgres_lock(db, name: str) -> None:
    from sqlalchemy import text

    from flowsint_crypto_compliance.storage.db_models import FinskalpSyncLock

    try:
        db.execute(text("SELECT pg_advisory_unlock(hashtext(:k))"), {"k": name})
    except Exception:
        db.rollback()
    row = db.get(FinskalpSyncLock, name)
    if row and row.holder_id == _holder_id():
        db.delete(row)
