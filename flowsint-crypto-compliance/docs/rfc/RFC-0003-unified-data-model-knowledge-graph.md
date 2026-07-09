# RFC-0003: Единая модель данных и граф знаний v2.0

**RFC-0003 · Unified Data Model & Knowledge Graph · v2.0**

| Поле | Значение |
|------|----------|
| Статус | **Complete (100%)** |
| Предшественники | [RFC-0000](RFC-0000-enterprise-constitution.md), [RFC-0002](RFC-0002-enterprise-architecture.md) |
| Реализация | `platform/v2/`, миграция `o7p8q9r0s1t2_rfc0003_knowledge_graph.py` |
| DoD | [`rfc0003-completion.md`](../architecture/v2/rfc0003-completion.md) |

---

## Предисловие

В платформе существуют только **сущности**, **отношения**, **события** и **доказательства**. Прямой обход ingest-пайплайна запрещён.

> **Принцип:** связь без доказательства не может считаться фактом.

---

## Глава 1. Единая модель знаний ✅

Пайплайн: получение → нормализация → качество → ER → связи → evidence → KG.

Код: `ingest_pipeline.py`, `event_subscriber.py`, `pipeline_chain.py`.

---

## Глава 2. Типы сущностей ✅

Полная таксономия в `canonical.py` → `EntityType`, `normalize_entity_type()`.

---

## Глава 3. Отношения ✅

`KnowledgeRelation` + `relation_types.py`. `link_relation()` → `RelationWithoutEvidenceError` без evidence.

---

## Глава 4. Evidence ✅

Расширенная модель: hash, signature, `original_uri`, retention, `valid_until`, `explain`.

---

## Глава 5. Entity Resolution ✅

11 сигналов, веса, `resolve_with_scoring()`, context (temporal/geo/behavioral).

---

## Глава 6. Knowledge Graph ✅

- Версии: `finskalp_entity_versions`, `finskalp_relation_versions`
- Снимки: `finskalp_graph_snapshots`
- **Temporal replay:** `reconstruct_graph_at()` — снимок или реконструкция из версий + events
- `POST /graph/snapshot` — создание снимка по требованию

---

## Глава 7. Fusion Engine ✅

Стадии RFC-0003: `CLEAN` … `GRAPH_PUBLISH`. По умолчанию: `FINSKALP_FUSION_MODE=rfc0003`.

---

## Глава 8. Confidence Model ✅

`confidence_model.py` → `ConfidenceBreakdown`, `calculate_confidence()`.

---

## Глава 9. История и воспроизводимость ✅

| Возможность | API |
|-------------|-----|
| История сущности | `GET /entities/{id}/history` |
| Сравнение версий | `GET /entities/{id}/compare` |
| История связи | `GET /relations/{id}/history` |
| Срез графа | `GET /graph/at?as_of=` |
| Экспорт доказательств | `GET /evidence/export` |

---

## Глава 10. Заключение ✅

Единое ядро: investigator → `PipelineChainOrchestrator` → KG → analytics → investigation → report.

---

## Приложение A. Целевая схема ✅

```
Источник → Событие → Нормализация → Entity Resolution → Knowledge Graph → Evidence → Analytics → Investigation → Report
```

- Manifest: `GET /api/platform/v2/pipeline-chain`
- Оркестратор: `platform/v2/pipeline_chain.py`
- Проводка: `finskalp_investigator.py`

---

## Production vs offline

| Режим | `FINSKALP_ENTITY_STORE` | Поведение |
|-------|---------------------------|-----------|
| Production | `postgres` (default) | Персистентный KG |
| Offline/dev | `memory` | In-memory + warning при старте |

Код: `entity_store_mode.py`, `warn_if_memory_store_in_production()`.

---

## Тесты

- `test_platform_v3_knowledge_graph.py`
- `test_rfc0002_0003_debt_closure.py`
- `test_rfc0003_100_percent.py`
