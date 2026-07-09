# FinSkalp Enterprise Architecture — Volume II Foundation

**RFC-0002 · Архитектура платформы второго поколения · v2.0**

| Поле | Значение |
|------|----------|
| Статус | Accepted (foundation) |
| Предшественники | [RFC-0000](RFC-0000-enterprise-constitution.md), [RFC-0001](RFC-0001-enterprise-architecture-audit.md) |
| Реализация | [`docs/architecture/v2/`](../architecture/v2/README.md), код `platform/v2/` |

---

## Предисловие

Архитектура — главный долгоживущий актив. Код, стек, UI и БД меняются; **модель расследования** должна оставаться стабильной.

Первое поколение доказало жизнеспособность OSINT, blockchain, OCR, compliance. Компоненты росли как **отдельные подсистемы**.

Второе поколение: **единая интеллектуальная экосистема**. Новый модуль — только как часть общей архитектуры.

---

## Глава 1. Архитектурная философия

Платформа занимается **расследованиями**, не «проверкой криптокошельков».

Blockchain, OSINT, OCR, sanctions, registry — **источники событий**. Расследование — центральный объект.

---

## Глава 2. Шесть уровней

| # | Уровень | Ответственность | Запрещено |
|---|---------|-----------------|-----------|
| L1 | **Data Acquisition** | Получение сырых данных | Анализ, риск, граф |
| L2 | **Intelligence Fusion** | validate → normalize → dedup → enrich → attribute → confidence → publish | Прямой обмен результатами между сервисами |
| L3 | **Knowledge** | Entity, relations, versions | Отдельные модели «кошелёк/телефон» |
| L4 | **Intelligence** | Risk, behavior, correlation, attribution, timeline, patterns, AI | Прямые вызовы внешних API |
| L5 | **Investigation** | Case, evidence, workflow, audit, review | — |
| L6 | **Presentation** | Web, REST, GraphQL, CLI, exports | Бизнес-логика |

Диаграмма: [`docs/architecture/v2/layers-and-domains.md`](../architecture/v2/layers-and-domains.md)

---

## Глава 3. Архитектурное ядро (5 компонентов)

1. **Intelligence Fusion Engine** — маршрутизатор всех данных
2. **Knowledge Graph** — хранилище знаний (не «база адресов»)
3. **Entity Resolution Engine** — слияние сигналов в одну Entity
4. **Evidence Center** — источник, время, trust, hash, связи
5. **Investigation Workspace** — рабочее место аналитика

---

## Глава 4. Единая ответственность

| Компонент | Только |
|-----------|--------|
| Fusion | Маршрутизация и обогащение |
| Graph | Хранение и запросы |
| Risk | Расчёт поверх графа |
| OSINT collectors | Сбор сырья |
| OCR | Извлечение текста |
| UI | Представление |

---

## Глава 5. Событийная модель

Все значимые изменения — **события**. Каталог: [`event-catalog.md`](../architecture/v2/event-catalog.md)

Примеры: `WalletDetected`, `EvidenceCreated`, `EntityMerged`, `CaseOpened`, `RiskUpdated`.

Код: `platform/v2/events.py`, адаптер `platform/v2/event_bus.py` → `ComplianceEventBus`.

---

## Глава 6–8. Домены DDD

| Домен | Слой |
|-------|------|
| Acquisition | L1 |
| Fusion | L2 |
| Knowledge | L3 |
| Analytics | L4 |
| Investigation | L5 |
| Presentation | L6 |
| Platform | cross-cutting (security, observability) |

Границы: [`domain-boundaries.md`](../architecture/v2/domain-boundaries.md)

---

## Глава 9–11. Контракты и каноническая модель

Взаимодействие только через **версионируемые контракты** (`platform/v2/contracts.py`).

Каноническая модель: [`canonical-model.md`](../architecture/v2/canonical-model.md)  
Типы: `platform/v2/canonical.py`  
Таблицы Postgres: миграция `n6o7p8q9r0s1_platform_canonical_v2`

---

## Глава 12–16. События, Gateway, плагины, отказоустойчивость, масштабирование

- **API Gateway:** единая точка входа — целевой `flowsint-api`; demo stand → thin BFF (см. migration)
- **Плагины:** `platform/v2/plugin_registry.py` — blockchain, OSINT, registry, OCR
- **Degradation:** circuit breakers, idempotency (уже в hardening)
- **Stateless compute:** Celery workers, горизонтальное масштабирование

---

## Глава 17. Архитектурные ограничения (обязательны)

- ❌ Новая модель без согласования с канонической
- ❌ Дублирование бизнес-логики
- ❌ Прямой доступ к чужой БД
- ❌ Сервис без API и документации
- ❌ Бизнес-логика в UI
- ❌ Необъяснимый risk score

---

## Глава 18. Заключение

После RFC-0002 FinSkalp — **операционная система расследований**, а не набор инструментов.

---

## Миграция с as-is (RFC-0001)

| Долг | Целевое состояние v2 | Фаза |
|------|---------------------|------|
| TD-C1 два Case | `Investigation` = workspace над `finskalp_entities` type=case | M2 |
| TD-C2 Evidence | `finskalp_evidence` + Evidence Center API | M1 |
| TD-C5 два API | Presentation → только gateway | M3 |
| TD-C4 цикл пакетов | `platform/v2` как shared kernel | M1 |

Дорожная карта: [`migration-phases.md`](../architecture/v2/migration-phases.md)

---

## Definition of Done (RFC-0002 foundation)

- [x] RFC документ и v2 specs
- [x] Канонические типы + каталог событий
- [x] Контракты доменов + plugin registry
- [x] Fusion pipeline router (stages)
- [x] Миграция canonical tables
- [x] Тесты scaffolding + integration
- [x] Dual-write OsintFinding → finskalp_evidence (Evidence Center)
- [x] PlatformEvent persist → finskalp_platform_events
- [x] Entity Resolution Engine
- [x] Knowledge Graph Store (Postgres)
- [x] Investigation Workspace (ComplianceCase bridge)
- [x] Neo4j unified projection (Finskalp* labels)
- [x] API Gateway /api/platform/v2/* (flowsint-api)
- [x] Demo routes Deprecation headers
- [x] compliance_rbac на mutating routes (TD-C3)
- [x] Event subscriber + CQRS timeline endpoint
- [x] data-flow-map.md + business-process-map.md
