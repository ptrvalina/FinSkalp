# Каталог сервисов FinSkalp

**RFC-0001 · Глава 8** · Статус: Draft · Дата: 2026-07-08

## Сводка

| Категория | Кол-во | Примечание |
|-----------|--------|------------|
| Deployable HTTP-сервисы | 3 | flowsint-api, regulator-stand, ml_server |
| Celery worker | 1 | Образ = flowsint-api |
| SPA | 1 | flowsint-app |
| Python-библиотеки | 4 | types, core, enrichers, crypto-compliance |
| Docker Compose стеки | 5 | dev, prod, hardening, tron, blockscout |

---

## 1. Прикладные сервисы

### flowsint-api

| Поле | Значение |
|------|----------|
| **Назначение** | Основной production API: расследования, граф (sketches), enrichers, flows, compliance |
| **Порт** | 5001 |
| **Стек** | FastAPI, Uvicorn, SQLAlchemy, JWT, SSE, Prometheus |
| **Владелец логики** | `flowsint-core` + `flowsint-crypto-compliance` |
| **Зависимости** | PostgreSQL, Redis, Neo4j |
| **Точки входа** | `flowsint-api/app/main.py` |
| **Auth** | JWT (`get_current_user`); RBAC частичный |

### flowsint-regulator-stand (FinSkalp demo/combat)

| Поле | Значение |
|------|----------|
| **Назначение** | Операционный центр ПОД/ФТ: inbox, FinSkalp investigate, OSINT, отчёты 115-ФЗ |
| **Порт** | 8877 (default `127.0.0.1`) |
| **Стек** | FastAPI + static SPA (`demo/static/`) |
| **Владелец логики** | `flowsint_crypto_compliance.demo.*` (~2100 LOC `web_server.py`) |
| **Зависимости** | Прямые Python-imports; опционально Postgres, Redis, Neo4j, Meilisearch |
| **Auth** | Опциональный Bearer (`FINSKALP_DEMO_API_TOKEN`); rate limit middleware |
| **Запуск** | `flowsint-crypto-compliance/scripts/start_demo_stand.bat` |

### flowsint-ml-serve

| Поле | Значение |
|------|----------|
| **Назначение** | ONNX scoring sidecar |
| **Порт** | 8891 |
| **Файл** | `services/ml_server.py` |
| **Критичность** | Опциональный — fallback в процессе |

### flowsint-app

| Поле | Значение |
|------|----------|
| **Назначение** | React UI: граф расследований + compliance dashboard |
| **Порт** | 5173 (dev) / 8080 (prod nginx) |
| **Интеграция** | Proxy `/api/` → flowsint-api; `VITE_COMPLIANCE_API` → stand :8877 |

---

## 2. Celery worker

| Поле | Значение |
|------|----------|
| **Образ** | Тот же, что flowsint-api |
| **Конфиг** | `flowsint-core/src/flowsint_core/core/celery.py` |
| **Broker** | Redis |
| **Очереди** | default, `scalpel-fusion`, `scalpel-enforcement`, per-collector `live-*` |

**Домены задач:** enrichers, flows, compliance fusion, batch screening, watchlist, Scalpel collectors, live collectors, enforcement ingest, multihop fusion, Maigret/SpiderFoot/OCR.

**Beat:** ежедневный enforcement ingest, hourly watchlist scan.

---

## 3. Python-модули (библиотеки)

| Модуль | Ответственность | Зависит от |
|--------|-----------------|------------|
| `flowsint-types` | Pydantic domain types | — |
| `flowsint-crypto-compliance` | FinSkalp engine: OSINT, fusion, risk, reports, attribution | types, core |
| `flowsint-core` | Platform core: ORM, Neo4j, Celery, auth helpers | enrichers, crypto-compliance |
| `flowsint-enrichers` | OSINT enricher plugins | types, core, crypto-compliance |

**Архитектурный риск:** цикл `core ↔ crypto-compliance ↔ enrichers` (см. [technical-debt.md](technical-debt.md#td-c4)).

---

## 4. Docker Compose

| Файл | Сервисы | Назначение |
|------|---------|------------|
| `docker-compose.yml` | postgres, redis, neo4j, app | Инфра + UI (без API) |
| `docker-compose.dev.yml` | + api, celery | Полный dev |
| `docker-compose.prod.yml` | postgres, redis, neo4j, api, celery, app | Production GHCR |
| `docker-compose.hardening.yml` | pghero, tempo, grafana, meilisearch, unleash | **Только standalone**, localhost ports |
| `flowsint-crypto-compliance/docker/docker-compose.tron-fullnode.yml` | tron-fullnode | Sovereign TRON |
| `flowsint-crypto-compliance/docker/docker-compose.blockscout.yml` | blockscout | Self-hosted EVM explorer |

### Инфраструктурные зависимости

| Сервис | Порт (host) | Критичность prod |
|--------|-------------|------------------|
| PostgreSQL | 127.0.0.1:5433 | Critical |
| Redis | 127.0.0.1:6379 | Critical (async) |
| Neo4j | 127.0.0.1:7474/7687 | Optional (memory fallback) |
| Meilisearch | 127.0.0.1:7700 | Optional |
| Tempo/Grafana | 127.0.0.1:4317/3001 | Optional |

---

## 5. Логическая схема

```
flowsint-app ──► flowsint-api :5001 ──► Postgres / Neo4j / Redis
                    │
                    └──► Celery worker ──► crypto-compliance tasks

flowsint-regulator-stand :8877 ──► crypto-compliance (direct imports)
                                 └──► Celery (async Scalpel)
```

---

## 6. Сервисы без реального runtime

| Элемент | Файл | Проблема |
|---------|------|----------|
| Synthetic microservices mesh | `demo/microservices.py` | Hardcoded metadata для UI, не service discovery |

---

## Следующий шаг (Volume II)

Единый **Service Registry** в коде + health per service, устранение дублирования demo stand vs flowsint-api.
