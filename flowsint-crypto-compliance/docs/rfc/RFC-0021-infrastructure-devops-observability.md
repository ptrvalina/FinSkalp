# RFC-0021: Infrastructure, DevOps & Observability v2.0

**RFC-0021 · IDOO · v2.0**

| Поле | Значение |
|------|----------|
| Статус | Accepted — Implemented (2026-07-09) |
| Предшественники | [RFC-0002](RFC-0002-enterprise-architecture.md), [RFC-0019](RFC-0019-api-sdk-plugin-platform.md), [RFC-0020](RFC-0020-enterprise-security-architecture.md) |
| Реализация | `platform/v2/idoo/` |
| Completion | [`rfc0021-completion.md`](../architecture/v2/rfc0021-completion.md) |

---

## Предисловие

IDOO — единая архитектура инфраструктуры, DevOps и наблюдаемости FinSkalp v2.0.

**Инфраструктура как код, GitOps и наблюдаемость по умолчанию.**

---

## Глава 1. Принципы инфраструктуры

`InfraPrinciple` — `principles.py`, `constraints.py`.

## Глава 2. Топология развёртывания

git → ci → artifact → cd → k8s → services → db → monitoring → backup → dr — `topology.py`.

## Глава 3. Контейнеры

flowsint-api, flowsint-app, flowsint-core — `containers.py`.

## Глава 4. Kubernetes

Deployment, StatefulSet, HPA, NetworkPolicy stubs — `kubernetes.py`.

## Глава 5. CI/CD

Pipeline stages + GitHub Actions — `cicd.py`.

## Глава 6. GitOps

Declarative config, Git as source of truth — `gitops.py`.

## Глава 7. Конфигурация окружений

dev/test/stage/prod, secrets via vault — `configuration.py`.

## Глава 8. Наблюдаемость

Metrics / logs / traces unified manifest — `observability.py`.

## Глава 9. Мониторинг

Health checks catalog (api, celery, postgres, redis, neo4j) — `monitoring.py`.

## Глава 10. Логирование

Structured JSON log schema — `logging.py`.

## Глава 11. Трейсинг

X-Correlation-ID propagation — `tracing.py`.

## Глава 12. Масштабирование

HPA rules per service — `scaling.py`.

## Глава 13. Очереди

Celery queue catalog from beat schedules — `queues.py`.

## Глава 14. Резервное копирование

postgres, neo4j, evidence, audit — `backup.py`.

## Глава 15. Аварийное восстановление

RTO/RPO targets — `disaster_recovery.py`.

## Глава 16. Операции

Runbook manifest per service — `operations.py`.

## Глава 17. Версионирование

Blue/green, canary, pyproject versions — `versioning.py`.

## Глава 18. SLA/SLO

API latency, queue throughput — `slo.py`.

## Глава 19. Ограничения

Forbidden infra practices — `constraints.py`.

---

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/platform/v2/idoo/manifest` | Full IDOO manifest |
| GET | `/api/platform/v2/idoo/health` | Platform health snapshot |
| GET | `/api/platform/v2/idoo/observability` | Observability snapshot |
| GET | `/api/platform/v2/idoo/cicd` | CI/CD pipeline manifest |
| GET | `/api/platform/v2/idoo/runbooks` | Operations runbooks |
| GET | `/api/platform/v2/idoo/queues` | Celery queue catalog |
| GET | `/api/platform/v2/idoo/backup` | Backup targets |

## Celery

| Task | Schedule | Description |
|------|----------|-------------|
| `idoo_health_probe_batch` | 120s | Periodic health probe for all services |

## Переиспользование

- `Makefile`, `docker-compose.dev.yml`, `docker-compose.prod.yml`, `docker-compose.hardening.yml`
- `flowsint-core/core/celery.py` beat schedules
- `platform/v2/routes.py` — X-Finskalp-Latency-Ms, X-Correlation-ID patterns
- `esa/siem.py`, `aspp/monitoring.py` — observability patterns
