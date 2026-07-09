# RFC-0007: Integration & Intelligence Connectors v2.0

**RFC-0007 · Connectors · v2.0**

| Поле | Значение |
|------|----------|
| Статус | Accepted — Implemented (2026-07-09) |
| Предшественники | [RFC-0003](RFC-0003-unified-data-model-knowledge-graph.md) … [RFC-0006](RFC-0006-intelligence-engine.md) |
| Реализация | `platform/v2/connectors/` |
| Completion | [`rfc0007-completion.md`](../architecture/v2/rfc0007-completion.md) |

---

## Предисловие

Архитектура второго поколения строится вокруг принципа **Connector First**. Любой внешний источник — подключаемый модуль через единый интерфейс.

---

## Главы 1–4

Коннектор обязан: получать → нормализовать → фиксировать источник → оценивать качество → публиковать в Fusion.

Путь данных: Source → Connector → Normalizer → Validator → Fusion → KG → Analytics.

---

## API

| Endpoint | Назначение |
|----------|------------|
| `GET /connectors/manifest` | Каталог всех коннекторов |
| `POST /connectors/{id}/health` | Health check |
| `POST /connectors/{id}/collect` | Collect + normalize + validate + publish |

---

## Заключение

Унифицированная система интеграций — новый источник подключается без изменения ядра.
