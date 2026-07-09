# FinSkalp — суверенный TRON FullNode (java-tron)

Локальный узел TRON Mainnet для on-chain запросов без зависимости от публичного TronGrid.

## Требования

- Docker Desktop / Docker Engine 24+
- **RAM:** 16 GB (лимит контейнера)
- **Диск:** от ~2 TB для полного снимка Mainnet (или меньше для lite-снимка)

## Быстрый старт (без снимка)

Синхронизация с genesis займёт дни. Для production используйте официальный снимок.

**Автоматизация:**

```bash
# Linux/macOS
./scripts/setup_sovereign_tron.sh

# Windows PowerShell
.\scripts\setup_sovereign_tron.ps1
```

**Makefile (из корня репозитория):**

```bash
make sovereign-tron-up
```

**Вручную:**

```bash
cd flowsint-crypto-compliance
docker compose -f docker/docker-compose.tron-fullnode.yml up -d
```

Проверка:

```bash
uv run python flowsint-crypto-compliance/scripts/tron_node_health.py
# или
curl http://127.0.0.1:8090/wallet/getnowblock -X POST -d '{}'
```

## Снимок базы (рекомендуется)

1. Скачайте снимок Mainnet: [https://database.tron.network/](https://database.tron.network/)
   (документация: [Mainnet backups](https://developers.tron.network/docs/mainnet-backups))
2. Распакуйте в локальную папку, например `./tron-data/output-directory`
3. Подключите том в `docker-compose.tron-fullnode.yml`:

```yaml
volumes:
  - ./tron-data/output-directory:/java-tron/output-directory
```

4. При необходимости укажите конфиг и datadir (пример из [tron-docker](https://github.com/tronprotocol/tron-docker/blob/main/single_node/README.md)):

```yaml
command: >
  -jvm "{-Xmx14g -Xms12g}"
  -d /java-tron/output-directory
```

5. **Health gate:** узел считается готовым для `FINSKALP_TRON_PROVIDER=sovereign`, когда `snapshot_gate_passed: true` в `GET /api/infra/tron-node` (блок ≥ `FINSKALP_TRON_SNAPSHOT_MIN_HEIGHT`, по умолчанию 70_000_000). До этого используйте `failover`.

```bash
uv run python scripts/tron_node_health.py
# exit 0 = reachable, 2 = reachable but still syncing snapshot
```

## Порты

| Порт  | Назначение                          |
|-------|-------------------------------------|
| 8090  | HTTP API (`/v1/*`, `/wallet/*`)     |
| 8091  | Solidity node HTTP                  |
| 18888 | P2P (TCP + UDP обязательны)         |
| 50051 | gRPC                                |

## Интеграция с FinSkalp

В корневом `.env`:

```env
FINSKALP_TRON_PROVIDER=failover
FINSKALP_TRON_SOVEREIGN_URL=http://127.0.0.1:8090
TRONGRID_API_KEY=...   # резерв при недоступности узла
```

Режимы `FINSKALP_TRON_PROVIDER`:

- `failover` (по умолчанию) — суверенный узел, при сбое TronGrid
- `sovereign` — только локальный узел
- `trongrid` — только TronGrid

Статус API демо-стенда: `GET http://localhost:8877/api/infra/tron-node`

Поля snapshot: `snapshot_sync_state` (`unreachable` | `syncing` | `ready`), `snapshot_gate_passed`, `snapshot_min_height`, `sovereign_peer_count`.

## Официальные ссылки

- Docker-образ: [tronprotocol/java-tron](https://hub.docker.com/r/tronprotocol/java-tron)
- Репозиторий: [tronprotocol/tron-docker](https://github.com/tronprotocol/tron-docker)
- Снимки: [database.tron.network](https://database.tron.network/)
