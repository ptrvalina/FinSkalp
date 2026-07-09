# Оптимальный техстек Flowsint Compliance

**Статус:** подтверждён · 2026-07-01  
**Вердикт:** Python/FastAPI + Celery/Redis + PostgreSQL + Neo4j + React/Vite, плюс **DuckDB/Parquet** для bulk staging суверенного реестра. Kafka, ClickHouse, k3s и self-hosted nodes — не в MVP, но интерфейсы проектируются без переписывания ядра.

---

## 1. Почему этот стек — оптимум

| Критерий | Решение |
|----------|---------|
| Совместимость с monorepo | `flowsint-api` уже на FastAPI, Celery, Redis, SQLAlchemy, Neo4j, SSE |
| Инфраструктура | `docker-compose.yml`: PostgreSQL 15, Redis, Neo4j 5 |
| UI | `flowsint-app`: React 19, Vite, `@xyflow/react`, TanStack Query |
| Регулятор | auditability, evidence chain, append-only audit log, reproducible fusion |
| Суверенность | только источники РФ/СНГ; иностранные KYT-вендоры **не интегрируются** |

---

## 2. Подтверждённые решения (5 пунктов)

| # | Вопрос | Решение |
|---|--------|---------|
| 1 | UI | Промышленный модуль в **`flowsint-app`**; regulator-stand — sales/demo |
| 2 | Очередь hub | **MVP без брокера** — JSONL + REST upload |
| 3 | Масштаб меток | **PostgreSQL** в pilot; ClickHouse — при факте нагрузки |
| 4 | Neo4j | **Один инстанс** с основным Flowsint |
| 5 | Деплой pilot | **docker compose** на одном сервере |

---

## 3. Целевая архитектура MVP

```
┌─────────────────────────────────────────────────────────────────────────┐
│  flowsint-app (React/Vite)  │  Regulator Stand (демо, FastAPI static)   │
└─────────────────────────────┴───────────────────────────────────────────┘
                                      │ HTTPS + JWT
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  flowsint-api · FastAPI  /api/compliance/*  ·  SSE (прогресс fusion)    │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Celery workers  │  │ flowsint-crypto │  │ flowsint-       │
│ fusion, import  │  │ -compliance     │  │ enrichers       │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
    ┌──────────────┬──────────────┬──────────────┬──────────────┐
    │ PostgreSQL 15│ Neo4j 5      │ Redis 7      │ DuckDB *     │
    │ cases, feeds │ graph UI     │ queue, cache │ Parquet bulk │
    │ registry     │ enrichments  │              │ staging      │
    └──────────────┴──────────────┴──────────────┴──────────────┘
    * DuckDB — in-process staging для bulk JSONL/CSV реестра
```

---

## 4. Backend

| Компонент | Стек |
|-----------|------|
| OSINT-ядро | **Python 3.12** — ingest, merge, **XGBoost** risk scoring, chain adapters |
| HTTP API | **FastAPI 0.115+**, Uvicorn в `flowsint-api` |
| Контракты | **Pydantic v2** (внутри) + **JSON Schema 2020-12** (`regulator-hub/v1`) |
| Фоновые задачи | **Celery 5 + Redis** — fusion, bulk import, graph export |
| Streaming | **SSE** (`sse-starlette`) — прогресс fusion |

---

## 5. Storage

### PostgreSQL 15 — system of record

| Таблица | Назначение |
|---------|------------|
| `compliance_cases` | Кейсы 115-ФЗ |
| `compliance_bank_feeds` | STR/SAR от банковского хаба |
| `compliance_registry_labels` | Суверенный реестр риск-меток (115-ФЗ, ФИУ, OSINT) |
| `compliance_fusion_runs` | Статус async fusion, celery task id, результат |
| `compliance_audit_log` | Append-only аудит действий аналитика |

### Neo4j 5 — investigation graph

Wallet, Subject, Bank, Platform, ControlPurchase, evidence edges → UI pivots в `flowsint-app`.

### Redis 7

Celery broker/result, hot cache address→label, rate-limit, SSE session state.

### DuckDB + Parquet — bulk staging

- Быстрое чтение JSONL/CSV snapshot реестра
- Дедупликация по `(chain, address)` с приоритетом confidence / sanctioned
- Batch upsert в PostgreSQL
- Удобно для air-gap файлов

---

## 6. Frontend

| Контур | Стек |
|--------|------|
| Промышленный UI | **React 19 + Vite + TypeScript** в `flowsint-app` |
| Граф | `@xyflow/react`, `react-force-graph-2d` |
| API state | TanStack Query |
| Demo-стенд | HTML + vanilla JS (`flowsint-regulator-stand`) |

---

## 7. Пакеты monorepo

| Пакет | Ответственность |
|-------|-----------------|
| `flowsint-types` | `SovereignRiskLabel`, `FusedAttribution`, `BankRegulatorFeed`, … |
| `flowsint-crypto-compliance` | OSINT core, ingest, storage, JSON Schema hub |
| `flowsint-enrichers` | `wallet_to_screening`, `fusion_enricher`, … |
| `flowsint-core` | Neo4j/PG clients, **Celery tasks** (`run_compliance_fusion`) |
| `flowsint-api` | REST `/api/compliance/*`, auth, upload |
| `flowsint-app` | Case UI, граф доказательств, отчёты 115-ФЗ |

**Паттерн:** modular monolith → логические микросервисы из демо = будущие границы деплоя.

---

## 8. API (MVP)

```
POST   /api/compliance/cases
GET    /api/compliance/cases/{id}
POST   /api/compliance/cases/{id}/bank-feeds
POST   /api/compliance/cases/{id}/fuse              # sync
POST   /api/compliance/cases/{id}/fuse/async        # Celery
GET    /api/compliance/cases/{id}/fusion-runs/{run_id}
POST   /api/compliance/cases/{id}/fuse/stream       # SSE
GET    /api/compliance/cases/{id}/graph
POST   /api/compliance/cases/{id}/graph/export
GET    /api/compliance/cases/{id}/report.json
POST   /api/compliance/registry/import
POST   /api/compliance/wallets/screen
```

---

## 9. Отчёты

| Формат | Стек |
|--------|------|
| JSON | Pydantic `model_dump` |
| PDF 115-ФЗ | **WeasyPrint** + Jinja2 (фаза B) |
| Excel | **openpyxl** |
| Graph export | Neo4j batch MERGE / JSON evidence graph |

---

## 10. Observability

| Уровень | Стек |
|---------|------|
| MVP | structured JSON logs + `/api/health` |
| Pilot/prod | Prometheus + Grafana |
| Трейсы | OpenTelemetry — только при multi-service |

---

## 11. Что не ставим в MVP

| Технология | Когда добавлять |
|------------|-----------------|
| Kafka/Redpanda | Continuous stream от десятков банков |
| ClickHouse | PostgreSQL узкое место по объёму меток |
| k3s/Kubernetes | HA production после pilot |
| Self-hosted chain nodes | Полный air-gap on-chain |
| Rust/Go | Не нужен для ядра |
| LLM в fusion | Только human summary, не для evidence |

---

## 12. Фазы реализации

### Фаза A — Foundation ✅

- [x] Pydantic-типы в `flowsint-types`
- [x] PostgreSQL миграции (`compliance_*`)
- [x] API cases + bank-feeds + fuse + registry import
- [x] JSON Schema validation hub v1
- [x] Celery task `run_compliance_fusion`
- [x] Unit-тесты MergeEngine + LinkScorer

### Фаза B — Fusion + Graph ✅ (в работе)

- [x] DuckDB/Parquet pipeline для bulk import реестра
- [x] Экспорт EvidenceGraph → Neo4j (`EvidenceGraphNeo4jExporter`)
- [x] API: `/graph`, `/graph/export`, `/fuse/stream` (SSE), `/report.json`
- [x] **XGBoost** risk model (`SovereignRiskModel`, sovereign-xgb-v1)
- [x] UI-модуль `/dashboard/compliance` в `flowsint-app`
- [x] In-memory demo API (`/api/compliance/*` на стенде 8877, `COMPLIANCE_DEMO_MODE` в API)
- [x] PDF/HTML 115-ФЗ (`pdf_report.py`, WeasyPrint опционально)
- [ ] Enrichers pivots → Neo4j graph — фаза C+

### Фаза C — Scale + Hub ✅ (pilot)

- [x] RegulatorAPIConnector (mTLS, `REGULATOR_HUB_URL`)
- [x] Hub stream consumer stub (Kafka/Redpanda, `KAFKA_BOOTSTRAP_SERVERS`)
- [x] Registry label indexes (Alembic `a9b0c1d2e3f4`)
- [x] Parquet import/export (`/registry/import/parquet`)
- [x] Excel отчёт (`/report.xlsx`, openpyxl)
- [x] Jinja2 PDF templates + WeasyPrint optional
- [x] Redis hot cache (`RedisLabelCache`, `REDIS_URL`)
- [x] Prometheus metrics (`/metrics`, `/api/compliance/metrics`)
- [x] SSE POST fusion with body + `scenario_id`
- [x] Neo4j enricher pivots (`ComplianceNeo4jPivotExporter`)
- [x] `flowsint-app` + `VITE_COMPLIANCE_API` для демо-стенда
- [x] Celery worker в `docker-compose.dev.yml`

### Фаза D — Air-gap hardening (позже)

- [ ] Self-hosted chain nodes
- [ ] Offline registry refresh workflow

---

## 13. Стек в одну строку

```
Python 3.12 · FastAPI · Celery/Redis · PostgreSQL 15 · Neo4j 5 · DuckDB/Parquet · XGBoost
· httpx · Pydantic v2 · JSON Schema · Alembic · React 19/Vite · JWT/mTLS
· Prometheus/Grafana · WeasyPrint · Vault (pilot+)
```

---

*Версия: 2026-07-01 · оптимальный стек подтверждён*
