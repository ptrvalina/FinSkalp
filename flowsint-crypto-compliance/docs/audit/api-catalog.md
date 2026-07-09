# Каталог API FinSkalp

**RFC-0001 · Глава 9** · Статус: Draft · Дата: 2026-07-08

## Сводка

| Поверхность | Префикс | Endpoints (≈) | Auth |
|-------------|---------|---------------|------|
| flowsint-api | `/api/*`, `/health` | ~95 | JWT (+ RBAC на ops) |
| regulator-stand | `/api/*` | ~91 + static | Optional token |
| compliance_api (mounted) | `/api/compliance/*` | ~22 | Нет (demo) |
| ml_server | `/health`, `/score` | 2 | Нет |

**Критическая находка:** две перекрывающиеся HTTP-поверхности compliance/OSINT — `:5001` и `:8877` с разными путями и auth.

---

## 1. flowsint-api (`flowsint-api/app/main.py`)

### 1.1 Platform core

| Домен | Prefix | Файл | Методы |
|-------|--------|------|--------|
| Health | `/health`, `/metrics` | `main.py` | GET |
| Auth | `/api/auth` | `routes/auth.py` | POST token/register, GET/PUT me |
| Investigations | `/api/investigations` | `routes/investigations.py` | CRUD + events |
| Sketches / graph | `/api/sketches` | `routes/sketches.py` | CRUD nodes/relations, import/export |
| Enrichers | `/api/enrichers` | `routes/enrichers.py` | GET, POST launch |
| Templates | `/api/enrichers/templates` | `routes/enricher_templates.py` | CRUD |
| Flows | `/api/flows` | `routes/flows.py` | CRUD, launch, compute |
| Events SSE | `/api/events` | `routes/events.py` | stream, logs |
| Analysis | `/api/analyses` | `routes/analysis.py` | CRUD |
| Chat | `/api/chats` | `routes/chat.py` | CRUD, stream |
| Scans | `/api/scans` | `routes/scan.py` | GET, DELETE |
| Keys vault | `/api/keys` | `routes/keys.py` | CRUD |
| Types | `/api/types`, `/api/custom-types` | `routes/types.py`, `custom_types.py` | registry |

### 1.2 Compliance (`/api/compliance`)

**Роутеры:** `compliance.py` + `compliance_ops.py` (общий prefix).

| Домен | Примеры | RBAC |
|-------|---------|------|
| Wallet screening | `POST /wallets/screen`, `/screen/batch` | JWT only в compliance.py |
| Cases | `POST/GET /cases`, `PATCH /cases/{id}` | ops: `require_permission` |
| Fusion | `POST /cases/{id}/fuse`, `/fuse/async`, `/fuse/stream` | JWT |
| Reports | `/report.json`, `/report.pdf`, `/report.xlsx`, `/report/fz115` | mixed |
| Workflow | `/workflow`, `/comments`, `/audit` | ops RBAC |
| Hub / webhooks | `/hub/webhook/{bank_id}`, `/webhooks/register` | ops |
| Watchlist | `/watchlist/subscribe`, `/watchlist/scan` | ops |
| Registry import | `/registry/import`, `/parquet` | JWT |
| Scalpel | `/scalpel/collect/async`, `/tasks/{id}` | JWT |
| Live collectors | `/live/collect`, `/live/fusion` | JWT |
| Scoring / OCR | `/scoring/predict`, `/ocr/extract` | JWT |
| Dashboard | `/dashboard/read-model` | JWT |
| SSE | `/events/stream` | JWT |

---

## 2. regulator-stand (`demo/web_server.py`)

### 2.1 Уникальные demo-only endpoints

| Домен | Path | Назначение |
|-------|------|------------|
| Investigate | `POST /api/finskalp/investigate` | Полный pipeline FinSkalp |
| Alias | `POST /api/osint/investigate` | **= тот же handler** |
| Inbox | `GET/PATCH /api/inbox/*` | STR workflow |
| Reports | `/api/inbox/{id}/forensic/pdf`, `/fz115/pdf` | PDF из inbox |
| Dashboard | `/api/dashboard`, `/api/feed/live` | Ops UI |
| OSINT quality | `/api/osint/fusion-explain`, `/evidence`, `/source-reliability` | RFC OSINT upgrade |
| Search | `GET /api/search` | Meilisearch + fallback |
| Health | `/api/health/live`, `/ready`, `/health` | Non-blocking probes |
| Interop | `/api/interop/ftm/*`, `/graphsense/*` | FTM / GraphSense bridges |

### 2.2 Дубли flowsint-api (другой prefix)

| Demo stand | flowsint-api equivalent |
|------------|-------------------------|
| `GET /api/scalpel/status` | `GET /api/compliance/scalpel/status` |
| `POST /api/scalpel/collect/async` | `POST /api/compliance/scalpel/collect/async` |
| `GET /api/graph/{case_ref}` | `GET /api/compliance/graph/{case_ref}` |
| `POST /api/live/fusion` | `POST /api/compliance/live/fusion` |
| `POST /api/wallet/screen` | `POST /api/compliance/wallets/screen` |
| `GET/POST /api/kyt/watchlist` | `GET/POST /api/compliance/watchlist` |

### 2.3 Известные дубликаты внутри stand

| Проблема | Evidence |
|----------|----------|
| `GET /api/scenarios` зарегистрирован дважды | `web_server.py` ~698 и ~2048 |
| Compliance router triplication | `compliance_api.py` + inline routes + flowsint-api |

---

## 3. Карта дублирования (RFC-0001 §9)

| Severity | Описание |
|----------|----------|
| **Critical** | Два gateway для одной доменной логики (5001 vs 8877) |
| **Critical** | UI может ходить в оба backend (`VITE_COMPLIANCE_API`) |
| **Significant** | Wallet screen / watchlist / graph — разные path, один сервисный класс |
| **Significant** | `compliance.py` без RBAC vs `compliance_ops.py` с RBAC |
| **Moderate** | Scenario runners: `/api/run/{id}` vs `/api/compliance/demo/run/{id}` |

---

## 4. API-first gap (RFC-0000 Principle 7)

Demo stand вызывает `FinSkalpInvestigator`, `OperationsCenter`, `ScalpelEngine` **напрямую через import**, не через flowsint-api.

**Следствие:** бизнес-логика в `web_server.py` отсутствует в production API.

---

## 5. Рекомендации (без реализации)

1. Канонический surface — **только** `flowsint-api`; stand = thin BFF или удалить дубли.
2. Единый prefix `/api/compliance/v1/...`.
3. OpenAPI merge: `flowsint-api` + deprecation list для stand-only routes.
4. RBAC на все mutating routes в `compliance.py`.

---

## Первоисточники

- `flowsint-api/app/api/routes/compliance.py`
- `flowsint-api/app/api/routes/compliance_ops.py`
- `flowsint-crypto-compliance/src/flowsint_crypto_compliance/demo/web_server.py`
- `flowsint-crypto-compliance/src/flowsint_crypto_compliance/demo/compliance_api.py`
- `flowsint-app/src/api/compliance-service.ts`
