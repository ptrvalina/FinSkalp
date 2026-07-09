# RFC-0013 Incremental Block Sync

**Статус:** Complete (100%)  
**Расширяет:** RFC-0012 Blockchain Intelligence Framework

## Что добавлено

- **Курсоры синхронизации** per chain (`BlockSyncStore`)
- **Инкрементальный sync** — от `last_block_height` до tip (batch)
- **Локальный индекс** transfers по адресам
- **Celery** `sync_blockchain_chains_incremental` + beat каждые 120с
- **API** status + manual run
- **Analyze** читает local index + adapter (merged)

## API

| Endpoint | Описание |
|----------|----------|
| `GET /blockchain-intelligence/sync/status` | Курсоры, метрики |
| `POST /blockchain-intelligence/sync/run` | Запуск sync (chains, simulate) |

## Completion

[`rfc0013-completion.md`](../architecture/v2/rfc0013-completion.md)
