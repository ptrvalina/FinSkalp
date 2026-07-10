# FinSkalp — Enterprise Readiness Roadmap

**Тип:** Дорожная карта готовности к enterprise-проду (аудит + план 30/60/90/180; без изменений кода)
**Дата:** 2026-07-09
**Исходная посылка:** FinSkalp — **production candidate**. **Запрещено:** полный рефакторинг, переписывание, удаление модулей, смена бизнес-логики. Цель — **минимальный набор** улучшений для перехода в **Enterprise Ready**.

Для каждого из 12 направлений: реализовано · отсутствует · критично · желательно · можно отложить.

Легенда критичности: 🔴 критично · 🟡 желательно · ⚪ отложить.

---

## 1. Security
- **Реализовано:** JWT (`:5001`, HS256, `AUTH_SECRET`, TTL 60ч), vault (AES-256-GCM+HKDF), CORS, harmonized RBAC на platform v2 (`:5001`), демо-hardening (rate-limit, security headers, опц. HSTS, input-validation).
- **Отсутствует:** auth/RBAC на демо `:8877` (`_noop_user`), реальный ESA middleware (`flowsint_api.middleware.auth` не существует), TLS в compose, rate-limit на `:5001`.
- **🔴 Критично:** закрыть демо-плоскость (auth/RBAC или за gateway как `:5001`); убрать default-ANALYST; TLS на периметре; rate-limit.
- **🟡 Желательно:** короче TTL + refresh/revocation; per-tenant лимиты.
- **⚪ Отложить:** mTLS между сервисами, полный ESA `evaluate_access` на каждом запросе.

## 2. Audit
- **Реализовано:** Postgres `ComplianceAuditLog` (создание кейса, ingest, fusion, просмотры), correlation_id, файловое OSINT-evidence с SHA-256 + manifest.
- **Отсутствует:** WORM/immutable (нет Object Lock / append-only триггеров / hash-chain), ESA/ECCF/EIA audit — in-memory, авто-аудит на каждом API-вызове, central SIEM.
- **🔴 Критично:** persist ESA/ECCF audit в Postgres; tamper-evident (hash-chain); enforce `audit:read`.
- **🟡 Желательно:** публикация событий в Redis Streams; auditor read-replica.
- **⚪ Отложить:** 7-летняя ретенция-автоматизация, legal hold.

## 3. RBAC
- **Реализовано:** compliance RBAC (`require_permission` на mutate `/api/compliance/*`), harmonized RBAC (RFC-0009) на platform v2 `:5001`, investigation RBAC (owner/editor/viewer).
- **Отсутствует:** RBAC на демо; `audit:read` не применяется; case-level access непоследователен; attribution confirm/reject на демо без user-dep.
- **🔴 Критично:** enforce `audit:read`; убрать default-ANALYST (явное назначение ролей).
- **🟡 Желательно:** admin-UI назначения ролей (`ComplianceUserRole` уже есть); ABAC через ESA `evaluate_access`.
- **⚪ Отложить:** dual-control для restricted exports.

## 4. Evidence
- **Реализовано:** OSINT-captures (ФС + хеши), KG (Postgres default), Postgres кейсы/фиды, опц. Neo4j-проекция, integrity-pipeline (`eccf/integrity.py` + Celery).
- **Отсутствует:** persistent ECCF-репозиторий (in-memory), object storage (S3/MinIO) для blob'ов, cross-region репликация.
- **🔴 Критично:** ECCF → Postgres WORM; blob-store для payload'ов.
- **🟡 Желательно:** ECCF↔KG bridge (уже работает при Postgres KG).
- **⚪ Отложить:** HSM-подпись manifest'ов.

## 5. API
- **Реализовано:** 3 плоскости (демо `:8877`, `:5001`, platform v2 BFF), FastAPI OpenAPI `/docs`, deprecation-заголовки на демо.
- **Отсутствует:** политика версионирования сверх `/v2`, rate-limit на `:5001`, единый authoritative-spec (ASPP-каталог декларативен).
- **🔴 Критично:** устранить dual-gateway drift (TD-C5) — привести `:8877` к auth-режиму `:5001` или спрятать за gateway.
- **🟡 Желательно:** rate-limit + версионная политика.
- **⚪ Отложить:** внешний API-gateway (Kong/WAF).

## 6. Monitoring
- **Реализовано:** `/health`, `/metrics` (Prometheus text), Docker healthchecks, pgHero (hardening), Grafana-дашборд JSON.
- **Отсутствует:** реальный Prometheus/Loki-сервер в compose; IDOO health-probe = stub (всегда HEALTHY); alert-rules/SLO-автоматизация.
- **🔴 Критично:** реальные health-probe (HTTP/DB/Redis/Neo4j); развернуть Prometheus + alert-rules.
- **🟡 Желательно:** SLO burn-rate, привязка дашбордов к реальным метрикам.
- **⚪ Отложить:** полный IDOO observability-стек.

## 7. Logging
- **Реализовано:** структурные JSON-логи (`JsonFormatter`, `finskalp.*`), correlation-id middleware на обоих API.
- **Отсутствует:** Loki (disabled, TD-IDOO-4), агрегация/ретенция, `trace_id`/`span_id` не заполняются без OTEL, часть legacy на `print`.
- **🔴 Критично:** централизованная агрегация логов (Loki + retention).
- **🟡 Желательно:** проброс correlation-id в Celery (частично есть); заполнение trace_id.
- **⚪ Отложить:** PII-redaction pipeline для логов.

## 8. CI/CD
- **Реализовано:** GitHub Actions (`tests.yml` — `make test`; `finskalp-compliance.yml` — subset; `images.yml` — build+push+Trivy на тегах), Makefile-паритет, Alembic-таргеты.
- **Отсутствует:** deploy-pipeline (staging/prod, migration-gate, smoke), интеграционные тесты с реальными Postgres/Redis/Neo4j, coverage-гейты. Compliance-CI гоняет ~4% тестов crypto-compliance.
- **🔴 Критично:** расширить CI до полного набора тестов + интеграционные сервисы.
- **🟡 Желательно:** deploy-workflow + migration-gate + coverage.
- **⚪ Отложить:** GitOps/blue-green, eval-gate автоматизация.

## 9. Backup
- **Реализовано:** persistent Docker volumes, Alembic (45 ревизий).
- **Отсутствует:** любые backup-скрипты (`pg_dump`/neo4j-dump/evidence-sync), `idoo/backup.py` — манифест на `s3://` без реализации, cron/CronJob, тестируемый restore.
- **🔴 Критично:** реальные backup-скрипты + тестируемый restore-путь.
- **🟡 Желательно:** расписание + offsite (S3).
- **⚪ Отложить:** ежемесячные restore-дриллы автоматом.

## 10. Disaster Recovery
- **Реализовано:** ничего операционного.
- **Отсутствует:** `disaster_recovery.py` — только манифест (`automated:False`, `last_tested:null`), нет репликации/failover/runbook-автоматизации.
- **🔴 Критично:** базовый DR-план + документированный (пусть ручной) restore из бэкапа.
- **🟡 Желательно:** async-репликация Postgres.
- **⚪ Отложить:** multi-AZ / cross-region, автоматический failover.

## 11. Scalability
- **Реализовано:** Celery + Redis (prod compose), async FastAPI, Redis Streams event-bus (in-memory fallback), Postgres entity-store по умолчанию.
- **Отсутствует:** горизонтальное масштабирование блокируется in-memory singletons (ECCF-репозиторий, ESA/EIA audit, RDE temporal, ICF scheduler, демо-сторы, IDOO-метрики).
- **🔴 Критично:** вынести stateful-синглтоны в Postgres/Redis (ECCF, audit, scheduler, temporal) — предпосылка HA.
- **🟡 Желательно:** distributed locks через Redis (частично есть — `FINSKALP_FUSION_LOCK_TTL_SEC`).
- **⚪ Отложить:** autoscaling-манифесты (декларативны).

## 12. Observability
- **Реализовано:** correlation-id, Prometheus-метрики, OTEL (opt-in, FastAPI+httpx), Tempo+Grafana (hardening), Celery-trace helpers, latency-заголовки.
- **Отсутствует:** Prometheus scrape-config, Loki, авто-экспорт трейсов в prod, привязанные SLO-дашборды. OTEL молча глотает ошибки инструментирования.
- **🔴 Критично:** включить OTEL по умолчанию в prod + scrape-config.
- **🟡 Желательно:** unified service-map, SLO-дашборды на реальных метриках.
- **⚪ Отложить:** полный three-pillar стек по манифесту IDOO.

---

## Планы по срокам

### 30 дней — «Закрыть критические дыры безопасности и доказательности»
| # | Задача | Направление | Разрыв |
|---|---|---|---|
| 1 | Закрыть демо `:8877` (auth/RBAC или за gateway) | Security/API | GAP-01/19 |
| 2 | Enforce `audit:read`, убрать default-ANALYST | RBAC | GAP-13 |
| 3 | ECCF-репозиторий → Postgres (persist) | Evidence | GAP-02 |
| 4 | ESA/ECCF audit → Postgres (persist) | Audit | GAP-03 |
| 5 | Реальные backup-скрипты `pg_dump`/neo4j + ручной restore | Backup/DR | GAP-04 |
| 6 | TLS на периметре + rate-limit `:5001` | Security | GAP-10 |

### 60 дней — «Целостность и наблюдаемость»
| # | Задача | Направление | Разрыв |
|---|---|---|---|
| 7 | Tamper-evident audit (hash-chain), общий ESA/ECCF/EIA | Audit | GAP-03 |
| 8 | Реальные IDOO health-probe (HTTP/DB/Redis/Neo4j) | Monitoring | GAP-09 |
| 9 | Prometheus + alert-rules + Loki в hardening-compose | Monitoring/Logging | GAP-20 |
| 10 | ESA как FastAPI middleware на `:5001` | Security | GAP-08 |
| 11 | Вынести in-memory singletons (scheduler/temporal) в Postgres/Redis | Scalability | GAP-11 |
| 12 | Расширить CI до полного набора тестов + интеграц. сервисы | CI/CD | GAP-12 |

### 90 дней — «Реальные данные и HA-готовность»
| # | Задача | Направление | Разрыв |
|---|---|---|---|
| 13 | Реальные адаптеры реестров/sanctions (ЕГРЮЛ/ЦБ/OpenSanctions) за флагом | Data/CRIF | GAP-05 |
| 14 | RDE: реальные CRIF-сигналы + persistent temporal | Data/RDE | GAP-05/11 |
| 15 | Object storage (S3/MinIO) для evidence-blob'ов | Evidence | GAP-02 |
| 16 | Deploy-pipeline (staging/prod + migration-gate + smoke) | CI/CD | GAP-12 |
| 17 | OTEL по умолчанию в prod + scrape-config + SLO-дашборды | Observability | GAP-20 |
| 18 | Единая сущность Case (миграция, аддитивно) | Архитектура | GAP-06 |

### 180 дней — «Enterprise-зрелость»
| # | Задача | Направление | Разрыв |
|---|---|---|---|
| 19 | Evidence first-class в БД + связка с отчётами | Архитектура | GAP-07 |
| 20 | Async-репликация Postgres + документированный DR-runbook | DR | GAP-24 |
| 21 | Реальный non-BTC block sync; ICF OCR подключён | Data | GAP-14/15 |
| 22 | Реальный LLM-путь EIA + SSE; EIA в UI | AI/UX | GAP-16/18 |
| 23 | Подключить RDE/ECCF/EIA к отчётам (enterprise-секции) | Reports | GAP-17 |
| 24 | IdP (Keycloak/OIDC) опц.; SIEM-экспорт | Security/Audit | GAP-22 |

**Можно отложить за горизонт 180 дней (после enterprise-ready):** ASPP GraphQL/gRPC/SDK/marketplace, mTLS/service mesh/FIDO2, ML-риск-модели (ONNX), cross-region DR / cold storage, разрыв package cycle (Plugin First).

---

## Критерий «Enterprise Ready»
Достигается по завершении 30+60+90-дневных волн:
- Нет плоскостей без auth; аудит персистентный и tamper-evident; evidence переживает рестарт/scale-out.
- Есть тестируемый backup/restore и базовый DR.
- Реальный мониторинг (Prometheus+alerts), логи агрегируются, health честный.
- CI гоняет полный набор + деплой с migration-gate.
- Данные комплаенса реальные (реестры/sanctions), RDE на реальных сигналах.

Всё — без нарушения бизнес-логики, доменов, API, RFC и имён сервисов; только эволюционные, обратносовместимые изменения.
