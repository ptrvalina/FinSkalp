"""RFC-0013 — Postgres-backed block sync store."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.sync_store import (
    BlockSyncStore,
    CanonicalBlockRecord,
    SyncCursor,
)


def _address_key(chain: str, address: str) -> str:
    return f"{chain.lower()}:{address.lower() if chain.lower() in ('eth', 'bsc', 'polygon') else address}"


class PostgresBlockSyncStore(BlockSyncStore):
    """Persists cursors, blocks, and transfer index to Postgres."""

    def __init__(self) -> None:
        super().__init__()
        self._db_available: bool | None = None

    def _can_use_db(self) -> bool:
        if self._db_available is not None:
            return self._db_available
        if os.getenv("FINSKALP_ENTITY_STORE", "").lower() in ("memory", "in_memory"):
            self._db_available = False
            return False
        try:
            from flowsint_core.core.postgre_db import SessionLocal

            db = SessionLocal()
            db.execute(__import__("sqlalchemy").text("SELECT 1"))
            db.close()
            self._db_available = True
        except Exception:
            self._db_available = False
        return self._db_available

    def _session(self):
        from flowsint_core.core.postgre_db import SessionLocal

        return SessionLocal()

    def get_cursor(self, chain: str) -> SyncCursor:
        key = chain.lower()
        if not self._can_use_db():
            return super().get_cursor(chain)
        from flowsint_crypto_compliance.storage.db_models import FinskalpBlockSyncCursor

        db = self._session()
        try:
            row = db.get(FinskalpBlockSyncCursor, key)
            if row:
                cur = SyncCursor(
                    chain=row.chain,
                    last_block_height=row.last_block_height,
                    last_block_hash=row.last_block_hash,
                    blocks_processed=row.blocks_processed,
                    transactions_processed=row.transactions_processed,
                    error_count=row.error_count,
                    updated_at=row.updated_at.isoformat() if row.updated_at else "",
                )
                self._cursors[key] = cur
                return cur
        finally:
            db.close()
        return super().get_cursor(chain)

    def update_cursor(
        self,
        chain: str,
        *,
        height: int,
        block_hash: str | None = None,
        blocks_delta: int = 0,
        txs_delta: int = 0,
        error: bool = False,
    ) -> SyncCursor:
        cur = super().update_cursor(
            chain,
            height=height,
            block_hash=block_hash,
            blocks_delta=blocks_delta,
            txs_delta=txs_delta,
            error=error,
        )
        if not self._can_use_db():
            return cur
        from flowsint_crypto_compliance.storage.db_models import FinskalpBlockSyncCursor

        db = self._session()
        try:
            key = chain.lower()
            row = db.get(FinskalpBlockSyncCursor, key)
            if row is None:
                row = FinskalpBlockSyncCursor(chain=key)
                db.add(row)
            row.last_block_height = cur.last_block_height
            row.last_block_hash = cur.last_block_hash
            row.blocks_processed = cur.blocks_processed
            row.transactions_processed = cur.transactions_processed
            row.error_count = cur.error_count
            row.updated_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        return cur

    def append_block(self, record: CanonicalBlockRecord) -> None:
        super().append_block(record)
        if not self._can_use_db():
            return
        from flowsint_crypto_compliance.storage.db_models import FinskalpChainBlock

        db = self._session()
        try:
            ts = None
            if record.timestamp:
                try:
                    ts = datetime.fromisoformat(record.timestamp.replace("Z", "+00:00"))
                except ValueError:
                    ts = None
            existing = (
                db.query(FinskalpChainBlock)
                .filter(
                    FinskalpChainBlock.chain == record.chain.lower(),
                    FinskalpChainBlock.height == record.height,
                )
                .first()
            )
            if existing is None:
                db.add(
                    FinskalpChainBlock(
                        chain=record.chain.lower(),
                        height=record.height,
                        block_hash=record.block_hash,
                        tx_count=record.tx_count,
                        block_timestamp=ts,
                        payload=record.payload,
                    )
                )
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def index_transfer(self, chain: str, transfer: dict[str, Any]) -> None:
        super().index_transfer(chain, transfer)
        if not self._can_use_db():
            return
        from flowsint_crypto_compliance.storage.db_models import FinskalpIndexedTransfer

        db = self._session()
        try:
            for addr in (transfer.get("source"), transfer.get("target")):
                if not addr:
                    continue
                db.add(
                    FinskalpIndexedTransfer(
                        chain=chain.lower(),
                        address_key=_address_key(chain, str(addr)),
                        tx_hash=str(transfer.get("tx_hash", "")),
                        source_address=str(transfer.get("source", "")),
                        target_address=str(transfer.get("target", "")),
                        asset=transfer.get("asset"),
                        amount=transfer.get("amount"),
                        block_height=transfer.get("block_height"),
                        payload=transfer,
                    )
                )
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def get_transfers_for_address(self, chain: str, address: str) -> list[dict[str, Any]]:
        memory_hits = super().get_transfers_for_address(chain, address)
        if not self._can_use_db():
            return memory_hits
        from flowsint_crypto_compliance.storage.db_models import FinskalpIndexedTransfer

        db = self._session()
        try:
            rows = (
                db.query(FinskalpIndexedTransfer)
                .filter(
                    FinskalpIndexedTransfer.chain == chain.lower(),
                    FinskalpIndexedTransfer.address_key == _address_key(chain, address),
                )
                .order_by(FinskalpIndexedTransfer.indexed_at.desc())
                .limit(200)
                .all()
            )
            db_hits = [
                {
                    "tx_hash": r.tx_hash,
                    "source": r.source_address,
                    "target": r.target_address,
                    "asset": r.asset,
                    "amount": r.amount,
                    "block_height": r.block_height,
                    **(r.payload or {}),
                }
                for r in rows
            ]
            if not db_hits:
                return memory_hits
            seen = {t.get("tx_hash") for t in memory_hits}
            merged = list(memory_hits)
            for t in db_hits:
                if t.get("tx_hash") not in seen:
                    merged.append(t)
            return merged[:200]
        finally:
            db.close()

    def status(self) -> dict[str, Any]:
        base = super().status()
        base["backend"] = "postgres" if self._can_use_db() else "memory"
        return base
