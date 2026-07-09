# RFC-0014: Intelligence Collection Framework v2.0

**RFC-0014 · ICF · v2.0**

| Поле | Значение |
|------|----------|
| Статус | Accepted — Implemented (2026-07-09) |
| Предшественники | [RFC-0007](RFC-0007-integration-connectors.md), [RFC-0003](RFC-0003-unified-data-model-knowledge-graph.md) |
| Реализация | `platform/v2/icf/` |
| Completion | [`rfc0014-completion.md`](../architecture/v2/rfc0014-completion.md) |

---

## Предисловие

Современные расследования требуют работы с большим количеством разнородных источников информации. Ценность платформы определяется способностью получать, нормализовать, сопоставлять и объяснять происхождение каждой единицы данных.

ICF рассматривает любой источник как **поставщика фактов**, а не как поставщика готовых выводов.

---

## Глава 1. Архитектурная модель

```
Source → Collector → Normalizer → Validator → Entity Extractor
  → Evidence Generator → Fusion Engine → Knowledge Graph
```

Каждый уровень выполняет строго определённую функцию.

---

## Глава 2. Категории источников

| Категория | Описание |
|-----------|----------|
| Blockchain | Публичные сети и блокчейн-эксплореры |
| Public Web | Открытые сайты, публичные API |
| News | Новостные публикации, пресс-релизы |
| Government Registries | Государственные реестры, лицензии |
| Corporate Data | Публичные сведения организаций |
| Documents | PDF, DOCX, XLSX, CSV, XML, JSON |
| Images | PNG, JPEG, TIFF, сканы |
| User Uploaded Evidence | Документы пользователя, архивы |

---

## Глава 3. Архитектура Collector

Обязательный интерфейс: `Initialize` → `Authenticate` → `Collect` → `Normalize` → `Validate` → `Publish` → `Shutdown`.

Реализация: `ICFCollector` оборачивает RFC-0007 `Connector`.

---

## Глава 4. Планировщик

`CollectionScheduler` — автоматический запуск, повторные проверки, rate limit, quota, retry.

---

## Главы 5–8. Обработка данных

- **Normalizer** — каноническая модель (Phone, Email, Wallet, Organization, Document)
- **Entity Extractor** — scalpel `extract_entities()` с provenance
- **Quality Engine** — completeness, freshness, origin, stability, error_rate, structure, repeatability
- **Evidence Generator** — id, source, discovered_at, acquisition_method, content_hash, version, original_uri, trust_level

---

## Глава 9. Fusion Integration

`fusion_bridge` запускает `fusion_pipeline` с `include_rfc0003=True`. Collector не выполняет fusion самостоятельно.

---

## Главы 10–11. Документы и изображения

- `DocumentProcessor` — OCR, text, table, requisite stubs
- `ImageProcessor` — OCR, QR, barcode stubs

---

## Главы 12–13. Monitoring и Security

- Per-collector metrics: latency, requests, errors, success rate, connection status
- Vault, TLS, rate limiting, input validation, service isolation

---

## Главы 14–16. SDK и Lifecycle

- Connector SDK extends RFC-0007
- Lifecycle: Draft → Testing → Production → Deprecated → Archived

---

## Главы 17–20. Метрики, производительность, ограничения

Collector **запрещено**: изменять Graph, Risk, Entity Resolution, принимать аналитические решения.

Celery beat: `icf_run_scheduled_collections` каждые 300 секунд.

---

## API

| Endpoint | Назначение |
|----------|------------|
| `GET /icf/manifest` | Манифест ICF v2.0 |
| `POST /icf/collect` | Полный конвейер сбора |
| `GET /icf/scheduler/status` | Статус планировщика |
| `POST /icf/scheduler/schedule` | Регистрация задачи |
| `GET /icf/monitoring` | Метрики коллекторов |

---

## Заключение

Универсальная платформа сбора информации — любой законный источник подключается как независимый модуль через единый конвейер обработки.
