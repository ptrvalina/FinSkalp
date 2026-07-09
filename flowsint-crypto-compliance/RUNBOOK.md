# FinSkalp Runbook — типовые инциденты

## 1. Redis недоступен

**Симптомы:** SSE-лента не обновляется, idempotency дубли, Celery broker down.

**Действия:**
1. Проверить `redis-cli ping` / health контейнера `redis`
2. Event bus деградирует в in-memory — перезапустить API после восстановления Redis
3. Celery worker: `uv run celery -A flowsint_core.core.celery worker` после broker UP

**Тест:** `pytest flowsint-crypto-compliance/tests/test_infrastructure.py`

---

## 2. Neo4j недоступен

**Симптомы:** `/api/compliance/graph` → source fusion_result, `neo4j` persist errors в логах.

**Действия:**
1. Fusion и скрининг **продолжают работать** — граф из Postgres JSON
2. Восстановить Neo4j: `docker compose up -d neo4j`
3. Повторный fusion перезапишет граф

---

## 3. Внешний коллектор (TronGrid / OpenSanctions)

**Симптомы:** `degraded: true` в ответе live collector, circuit breaker open.

**Действия:**
1. `GET /api/compliance/circuit-breakers/status`
2. Дождаться recovery (default 60s) или снизить `FINSKALP_CB_FAILURE_THRESHOLD`
3. Расследование продолжается с остальными источниками Scalpel

---

## 4. Batch screening > 10k адресов

**Симптомы:** HTTP 422, очередь Celery перегружена.

**Действия:**
1. Разбить CSV на части ≤ 10k
2. Масштабировать workers: `--concurrency=4` на queue default
3. k6 SLO: `k6 run flowsint-crypto-compliance/k6/batch-screening.js`

---

## 5. SLA breach на делах

**Симптомы:** `sla_breached=true`, metric `compliance_sla_breach_total` растёт.

**Действия:**
1. `GET /api/compliance/cases?workflow_status=investigating`
2. Назначить assignee: `PATCH /api/compliance/cases/{id}` → `pending_filing`
3. Эскалация compliance officer через SSE event `case_status_changed`

---

## 6. Webhook банка — invalid signature

**Симптомы:** HTTP 401 на `POST /api/compliance/hub/webhook/{bank_id}`.

**Действия:**
1. Проверить `COMPLIANCE_WEBHOOK_SECRET_{BANK_ID}` или Vault key `webhook:{bank_id}`
2. Header `X-Hub-Signature: sha256=<hmac-sha256(body)>`
3. Idempotency: `X-Idempotency-Key` для повторов

---

## 7. Миграции

```bash
cd flowsint-api && uv run alembic upgrade head
```

Revision chain: `e7f8…` → `f8a9…` → `g9h0…` → `h0i1…` (workflow/RBAC/batch/watchlist)

---

## 8. Суверенный TRON-узел (java-tron)

**Симптомы:** `sovereign_reachable: false` в `GET /api/infra/tron-node`, отчёты с меткой «TronGrid (failover)».

**Действия:**
1. Запустить FullNode: `docker compose -f flowsint-crypto-compliance/docker/docker-compose.tron-fullnode.yml up -d`
2. Проверить: `uv run python flowsint-crypto-compliance/scripts/tron_node_health.py`
3. В `.env`: `FINSKALP_TRON_PROVIDER=failover`, `FINSKALP_TRON_SOVEREIGN_URL=http://127.0.0.1:8090`
4. Снимок Mainnet (ускорение): см. `flowsint-crypto-compliance/docker/tron-fullnode/README.md` и [database.tron.network](https://database.tron.network/)

**Без узла:** failover автоматически переключается на TronGrid (`TRONGRID_API_KEY`).

---

## Observability

- Logs: JSON stdout, header `X-Correlation-ID`
- Metrics: `GET /metrics` или `/api/compliance/metrics`
- OTel (optional): `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel:4317`
