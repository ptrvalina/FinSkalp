# FinSkalp — Architecture Audit Artifacts (RFC-0001)

Рабочая папка артефактов [RFC-0001 Enterprise Architecture Audit](../rfc/RFC-0001-enterprise-architecture-audit.md).

**Статус:** Draft — инвентаризация выполнена 2026-07-08. Новый функционал на этом этапе **не разрабатывается**.

## Начать здесь

👉 **[Executive Summary](executive-summary.md)**

## Артефакты (Глава 16)

| # | Артефакт | Файл | Статус |
|---|----------|------|--------|
| — | Сводка для руководства | [executive-summary.md](executive-summary.md) | Draft |
| 1 | Каталог сервисов | [service-catalog.md](service-catalog.md) | Draft |
| 2 | Каталог API | [api-catalog.md](api-catalog.md) | Draft |
| 3 | Схема моделей данных | [data-model-map.md](data-model-map.md) | Draft |
| 4 | Внешние интеграции | [external-integrations.md](external-integrations.md) | Draft |
| 5 | Технический долг + риски | [technical-debt.md](technical-debt.md) | Draft |
| 6 | Безопасность | [security-report.md](security-report.md) | Draft |
| 7 | Производительность | [performance-map.md](performance-map.md) | Draft |
| 8 | Карта потоков данных | — | Planned (Volume II) |
| 9 | Карта бизнес-процессов | — | Planned (Volume II) |
| 10 | Рекомендации Enterprise Architecture | см. technical-debt.md § Volume II | Planned |

## Definition of Done (RFC-0001)

- [x] Каталог сервисов заполнен
- [x] Каталог API заполнен
- [x] Схема моделей данных согласована с RFC-0000
- [x] Карта технического долга с классификацией рисков
- [x] Отчёты по безопасности и производительности
- [ ] Рекомендации по переходу к Volume II утверждены CAO
- [ ] Карты потоков данных и бизнес-процессов

## Методология

Аудит проведён по исходному коду, compose, миграциям Alembic, Neo4j migrations, SECURITY_AUDIT.md, HARDENING.md — без изменения моделей (Глава 10).
