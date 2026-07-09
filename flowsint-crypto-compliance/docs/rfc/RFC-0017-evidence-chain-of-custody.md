# RFC-0017: Evidence & Chain of Custody Framework v2.0

**RFC-0017 · ECCF · v2.0**

| Поле | Значение |
|------|----------|
| Статус | Accepted — Implemented (2026-07-09) |
| Предшественники | [RFC-0002](RFC-0002-enterprise-architecture.md), [RFC-0003](RFC-0003-unified-data-model-knowledge-graph.md), [RFC-0014](RFC-0014-intelligence-collection-framework.md), [RFC-0015](RFC-0015-compliance-registry-intelligence.md) |
| Реализация | `platform/v2/eccf/` |
| Completion | [`rfc0017-completion.md`](../architecture/v2/rfc0017-completion.md) |

---

## Предисловие

ECCF обеспечивает полный жизненный цикл доказательств: от сбора до архивации с неизменяемым содержимым, аудитом и цепочкой хранения.

**Доказательства неизменяемы — каждое действие фиксируется в аудите.**

---

## Глава 1. Архитектурная модель

```
Source → Collector → Evidence Generator → Repository → Integrity
  → Knowledge Graph → Timeline → Report → Archive
```

Входные подсистемы: icf, crif, blockchain_intelligence, evidence_center, knowledge_store, ingest_pipeline.

---

## Глава 2. Категории доказательств

| Категория | Источник |
|-----------|----------|
| blockchain | Blockchain Intelligence |
| registry | CRIF |
| document | OCR / PDF / контракты |
| osint | ICF / публичные источники |
| user | Загрузки аналитика |

---

## Глава 3. Идентификаторы

Формат: `EV-YYYY-NNNNNNNNNNNN` (12-значный sequence).

Пример: `EV-2026-000000000001`

---

## Глава 4. Жизненный цикл

`draft → registered → validated → linked → in_report → archived`

---

## Глава 5. Генератор доказательств

`generator.generate_evidence()` — из collector payload с `content_hash_from_finding`.

---

## Глава 6. Репозиторий

In-memory store + optional `knowledge_store.store_evidence` bridge. Дедупликация по `(tenant_id, content_hash)`.

---

## Глава 7. Целостность

`integrity.verify_integrity()` — hash, size, mime consistency.

---

## Глава 8. Версионирование

`versioning.create_new_version()` — prior version immutable, metadata diff.

---

## Глава 9. Провенанс

`provenance.build_provenance()` — who, when, how, from_where, derived_from.

---

## Глава 10. Аудит

Append-only `AuditEntry`: Created, HashCalculated, Validated, Linked, UsedInReport, Archived.

---

## Глава 11. Timeline

Хронология событий per evidence.

---

## Глава 12. Knowledge Graph

`graph_bridge.link_evidence_to_entities()` — только через `ingest_pipeline`, без прямой мутации графа.

---

## Глава 13. Отчёты

`report_bridge.record_report_usage(evidence_id, report_id, analyst)`.

---

## Глава 14. Архив

`archive.archive_evidence()` + `search_archive()`.

---

## Глава 15. RBAC

Права: view, use, export, comment, archive, register.

---

## Глава 16. Мониторинг

`monitoring.ECCFMetrics` — registered, deduplicated, integrity_failures, archived, kg_linked.

---

## Глава 17. API

| Метод | Endpoint |
|-------|----------|
| GET | `/api/platform/v2/eccf/manifest` |
| POST | `/api/platform/v2/eccf/register` |
| GET | `/api/platform/v2/eccf/{evidence_id}` |
| POST | `/api/platform/v2/eccf/{evidence_id}/verify` |
| GET | `/api/platform/v2/eccf/{evidence_id}/audit` |
| GET | `/api/platform/v2/eccf/{evidence_id}/timeline` |
| POST | `/api/platform/v2/eccf/{evidence_id}/archive` |
| POST | `/api/platform/v2/eccf/report-usage` |
| GET | `/api/platform/v2/eccf/monitoring` |

---

## Глава 18. Архитектурные ограничения

Запрещено: delete_evidence, modify_content, bypass_audit_trail, direct_graph_mutation.

---

## Глава 19. Celery

`eccf_verify_integrity_batch` — beat 1800s (30 min).

---

## Глава 20. Заключение

ECCF v2.0 реализует полную цепочку хранения доказательств с неизменяемым содержимым и append-only аудитом.
