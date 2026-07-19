# FinSkalp

**FinSkalp** — платформа крипто-комплаенса и расследований для регуляторов и аналитиков: fiat↔crypto скрининг, граф знаний, OSINT, blockchain intelligence и рабочее место аналитика.

Репозиторий: https://github.com/ptrvalina/FinSkalp

## Возможности

- **Compliance** — кейсы, скрининг адресов, fusion-анализ, workflow и SLA
- **Platform v2** — Knowledge Graph, Intelligence Engine, Investigation Workspace, RBAC, Design System
- **Blockchain Intelligence** — мультичейн-анализ, инкрементальная синхронизация блоков (RFC-0012/0013)
- **OSINT** — enrichers, граф расследований, визуализация связей
- **Analyst Workspace** — единая оболочка, command palette, синхронизация вкладок

## Быстрый старт

### Требования

- Docker и Make (или ручной запуск через `uv` / `npm`)
- PostgreSQL, Redis, Neo4j (через docker-compose)

### Linux / macOS

```bash
git clone https://github.com/ptrvalina/FinSkalp.git
cd FinSkalp
make dev
```

### Windows

```powershell
git clone https://github.com/ptrvalina/FinSkalp.git
cd FinSkalp
copy .env.example flowsint-api\.env
copy .env.example flowsint-core\.env
copy .env.example flowsint-app\.env
docker compose -f docker-compose.dev.yml up --build
```

UI: http://localhost:5173  
API: http://localhost:5001  

Логин демо (после `make seed` / первого старта): см. seed-скрипты / `analyst@example.com`.

Режим **combat** по умолчанию (`COMPLIANCE_COMBAT_MODE=1`): live OSINT/on-chain коллекторы, без synthetic demo-сценариев для боевых кейсов `FSK-*`.

### Crypto-compliance (standalone)

```bash
cd flowsint-crypto-compliance
uv sync
uv run pytest -q
```

Документация: `flowsint-crypto-compliance/README.md`, `flowsint-crypto-compliance/docs/rfc/`

## Структура монорепо

| Пакет | Назначение |
|-------|------------|
| `flowsint-app` | Frontend (React) |
| `flowsint-api` | FastAPI, compliance и platform v2 API |
| `flowsint-core` | Celery, orchestrator, vault |
| `flowsint-enrichers` | OSINT enrichers |
| `flowsint-types` | Pydantic-модели |
| `flowsint-crypto-compliance` | FinSkalp compliance engine, RFC v2 |

> Внутренние имена пакетов `flowsint-*` — технический слой платформы; продукт и UI брендируются как **FinSkalp**.

## Переменные окружения

См. `.env.example`. Ключевые:

- `FINSKALP_ENTITY_STORE` — `memory` (dev) или Postgres (prod)
- `FINSKALP_BLOCK_SYNC_BATCH` — размер батча block sync
- `DATABASE_URL`, `REDIS_URL`, `NEO4J_URI`

## Лицензия

Apache-2.0 — см. [LICENSE](./LICENSE). Использование только в законных целях — см. [ETHICS.md](./ETHICS.md).
