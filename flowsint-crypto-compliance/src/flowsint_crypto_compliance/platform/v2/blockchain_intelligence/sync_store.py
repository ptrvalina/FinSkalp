"""RFC-0013 — incremental block sync store (memory + Postgres)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_store: "BlockSyncStore | None" = None


@dataclass
class SyncCursor:
    chain: str
    last_block_height: int = 0
    last_block_hash: str | None = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    blocks_processed: int = 0
    transactions_processed: int = 0
    error_count: int = 0


@dataclass
class CanonicalBlockRecord:
    chain: str
    height: int
    block_hash: str
    timestamp: str | None
    tx_count: int
    payload: dict[str, Any] = field(default_factory=dict)


class BlockSyncStore:
    """Block index with per-chain cursors and address→transfer index."""

    def __init__(self) -> None:
        self._cursors: dict[str, SyncCursor] = {}
        self._blocks: dict[str, list[CanonicalBlockRecord]] = {}
        self._transfers_by_address: dict[str, list[dict[str, Any]]] = {}

    def get_cursor(self, chain: str) -> SyncCursor:
        key = chain.lower()
        if key not in self._cursors:
            self._cursors[key] = SyncCursor(chain=key)
        return self._cursors[key]

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
        cur = self.get_cursor(chain)
        cur.last_block_height = height
        if block_hash:
            cur.last_block_hash = block_hash
        cur.blocks_processed += blocks_delta
        cur.transactions_processed += txs_delta
        if error:
            cur.error_count += 1
        cur.updated_at = datetime.now(timezone.utc).isoformat()
        return cur

    def append_block(self, record: CanonicalBlockRecord) -> None:
        chain = record.chain.lower()
        self._blocks.setdefault(chain, []).append(record)
        if len(self._blocks[chain]) > 500:
            self._blocks[chain] = self._blocks[chain][-500:]

    def index_transfer(self, chain: str, transfer: dict[str, Any]) -> None:
        for addr in (transfer.get("source"), transfer.get("target")):
            if not addr:
                continue
            key = f"{chain.lower()}:{addr.lower() if chain.lower() in ('eth', 'bsc', 'polygon') else addr}"
            self._transfers_by_address.setdefault(key, []).append(transfer)
            if len(self._transfers_by_address[key]) > 200:
                self._transfers_by_address[key] = self._transfers_by_address[key][-200:]

    def get_transfers_for_address(self, chain: str, address: str) -> list[dict[str, Any]]:
        key = f"{chain.lower()}:{address.lower() if chain.lower() in ('eth', 'bsc', 'polygon') else address}"
        return list(self._transfers_by_address.get(key, []))

    def status(self) -> dict[str, Any]:
        return {
            "backend": "memory",
            "chains": [
                {
                    "chain": c.chain,
                    "last_block_height": c.last_block_height,
                    "last_block_hash": c.last_block_hash,
                    "blocks_processed": c.blocks_processed,
                    "transactions_processed": c.transactions_processed,
                    "error_count": c.error_count,
                    "updated_at": c.updated_at,
                    "indexed_blocks": len(self._blocks.get(c.chain, [])),
                }
                for c in self._cursors.values()
            ],
            "total_indexed_transfers": sum(len(v) for v in self._transfers_by_address.values()),
        }

    def reset(self) -> None:
        self._cursors.clear()
        self._blocks.clear()
        self._transfers_by_address.clear()


def get_block_sync_store() -> BlockSyncStore:
    global _store
    if _store is None:
        if os.getenv("FINSKALP_ENTITY_STORE", "").lower() in ("memory", "in_memory"):
            _store = BlockSyncStore()
        else:
            from flowsint_crypto_compliance.platform.v2.blockchain_intelligence.postgres_sync import (
                PostgresBlockSyncStore,
            )

            _store = PostgresBlockSyncStore()
    return _store


def reset_block_sync_store() -> None:
    global _store
    if _store is not None:
        _store.reset()
    _store = None
