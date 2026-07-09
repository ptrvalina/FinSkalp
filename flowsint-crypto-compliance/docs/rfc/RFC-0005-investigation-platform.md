# RFC-0005: Investigation Platform & Enterprise Operations v2.0

**RFC-0005 · Investigation Platform · v2.0**

| Поле | Значение |
|------|----------|
| Статус | Accepted — Implemented (2026-07-08) |
| Предшественники | [RFC-0000](RFC-0000-enterprise-constitution.md) … [RFC-0004](RFC-0004-intelligence-platform.md) |
| Реализация | `platform/v2/investigation_platform/`, `investigation_workspace.py`, `evidence_center.py` |
| Completion | [`rfc0005-completion.md`](../architecture/v2/rfc0005-completion.md) |

---

## Предисловие

Архитектура данных и интеллектуальные алгоритмы сами по себе не создают ценности.

Ценность возникает только тогда, когда аналитик способен использовать результаты анализа в реальном расследовании, формировать доказательную базу, принимать решения, документировать ход работы и передавать материалы другим подразделениям.

Поэтому заключительным элементом архитектуры второго поколения FinSkalp становится операционный уровень платформы.

Именно здесь объединяются все предыдущие RFC.

Knowledge Graph становится рабочим инструментом.

Fusion Engine становится поставщиком фактов.

Risk Engine становится помощником аналитика.

Evidence Center становится единым хранилищем доказательств.

Case Management становится ядром ежедневной работы.

С этого момента пользователь больше не взаимодействует с отдельными сервисами.

Он работает исключительно с расследованием.

---

## Глава 1. Investigation First

В центре платформы находится не кошелёк, не транзакция и не человек.

В центре платформы находится расследование (Investigation).

Каждое расследование объединяет: цели, участников, объекты анализа, доказательства, версии, события, временную шкалу, выводы, рекомендации, итоговый отчёт.

**Правило:** любая информация существует только в контексте расследования или связана с одним или несколькими расследованиями.

---

## Глава 2. Case Management

Стадии жизненного цикла (реализация: `services/case_workflow.py`):

| Код | Стадия |
|-----|--------|
| `new` | Новое дело |
| `triage` | Предварительный анализ |
| `investigating` | Активное расследование |
| `pending_filing` | Дополнительная проверка |
| `internal_review` | Внутреннее согласование |
| `filed` | Завершено |
| `archived` | Архив |

Все изменения статуса фиксируются в журнале аудита (`compliance_audit_log`).

---

## Глава 3. Evidence Center

Единое хранилище доказательств. Удаление запрещено — только смена статуса с полной историей.

API: `POST/GET /api/platform/v2/investigations/{case_ref}/evidence`, `PATCH /api/platform/v2/evidence/{id}/status`

---

## Глава 4. Timeline Engine

Временная шкала расследования: транзакции, публикации, документы, действия пользователей, результаты анализа.

API: `GET /api/platform/v2/cases/{case_ref}/timeline` (воспроизведение по дате — параметр `at` в service).

---

## Глава 5. Workspace аналитика

10 панелей: карточка дела, граф, timeline, доказательства, потоки, гипотезы, рекомендации ИИ, журнал, поиск, отчёты.

API: `GET /api/platform/v2/investigations/{case_ref}/workspace`

---

## Глава 6. Explainable Investigation

API: `GET /api/platform/v2/investigations/{case_ref}/explain/{entity_id}`

---

## Главы 7–13

- **Совместная работа** — комментарии, assignee, audit (compliance API)
- **Отчёты** — 8 типов, `/api/compliance/cases/{id}/report.*`
- **Безопасность** — RBAC, audit, evidence hash
- **Эксплуатация** — `GET /api/platform/v2/operations/manifest`
- **Наблюдаемость** — Prometheus, OTLP, Grafana
- **Платформа как продукт** — единая модель, API, тесты
- **Дорожная карта** — 9-этапный release cycle в manifest

---

## Заключение

Настоящий RFC завершает формирование архитектуры второго поколения FinSkalp.

Платформа получает единую архитектурную модель, граф знаний, интеллектуальные движки, пространство расследований, Evidence Center и промышленную модель эксплуатации.

---

## Приложение A. API

| Endpoint | Назначение |
|----------|------------|
| `GET /investigation/manifest` | Каталог RFC-0005 |
| `GET /investigations/{case_ref}/workspace` | Рабочее пространство |
| `GET/POST /investigations/{case_ref}/evidence` | Evidence Center |
| `PATCH /evidence/{id}/status` | Смена статуса |
| `GET /cases/{case_ref}/timeline` | Timeline |
| `GET /investigations/{case_ref}/explain/{entity_id}` | Explain |
| `GET /operations/manifest` | Enterprise ops |

## Приложение B. Definition of Done

См. [`rfc0005-completion.md`](../architecture/v2/rfc0005-completion.md) — все пункты ✅
