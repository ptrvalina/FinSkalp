# RFC-0013 Incremental Block Sync — 100% Completion Checklist

Дата: 2026-07-09

- ✅ `sync_store.py` — cursors, blocks, address index
- ✅ `block_sync.py` — incremental sync (BTC live + simulate fallback)
- ✅ `sync_blockchain_chains_incremental` Celery task
- ✅ Celery beat 120s
- ✅ `GET /sync/status`, `POST /sync/run`
- ✅ `analyze` merges `local_index` + adapter
- ✅ Manifest `incremental_sync` block
- ✅ `tests/test_rfc0013_block_sync.py`
- ✅ `postgres_sync.py` — Postgres-backed cursors, blocks, transfer index
- ✅ `sync_lock.py` — per-chain distributed lock (memory + Postgres advisory/lease)
- ✅ Alembic migration `p8q9r0s1t2u3_rfc0013_block_sync.py`

## Prod notes

- BTC: Blockstream API для tip + block txs
- ETH/BSC/Polygon: Blockscout stats
- TRON: TronGrid getnowblock
- `FINSKALP_BLOCK_SYNC_BATCH` — размер батча (default 5)
- `FINSKALP_ENTITY_STORE=memory` — in-memory store (dev/tests); omit for Postgres persistence
- `FINSKALP_SYNC_LOCK_TTL` — lease TTL for Postgres row-level lock fallback (default 300s)
