# Закрытие техдолга RFC-0002 / RFC-0003

**Дата:** 2026-07-08 · **Статус:** Закрыто (M2–M3 scope)

## Область

Закрыты пункты техдолга, относящиеся к внедрению RFC-0002 (Entity First, unified projection) и RFC-0003 (Knowledge Graph, mandatory ingest, ER, graph versioning).

## Реализовано

| Область | Изменение |
|---------|-----------|
| KG Postgres по умолчанию | `get_knowledge_graph_store()` читает `FINSKALP_ENTITY_STORE` (default `postgres`) |
| Mandatory ingest | `FinSkalpInvestigator`, `FusionPipeline.with_rfc0003_path()`, `PlatformEventSubscriber` |
| Entity labels → KG | `platform/v2/entity_label_bridge.py` синхронизирует `EntityLabel` в canonical `Entity` |
| Neo4j unified | `Neo4jUnifiedProjection` + facade `WalletNeo4jStore`; `project_evidence_graph()` в compliance services |
| Entity Resolution Ch.7 | `score_match(context=...)` — TEMPORAL / GEO / BEHAVIORAL weights |
| Graph versioning Ch.6 | auto `record_entity_version` / `record_relation_version` на upsert/link |
| API BFF (TD-C5) | `platform/v2/routes.py` — общий router для flowsint-api и demo stand |
| UI | секция «Граф знаний» в `compliance-page.tsx` |
| Hub ingest alias | `HubIngestPipeline` + `IngestPipeline` alias в `ingestion/pipeline.py` |

## Закрытые пункты technical-debt.md

- **TD-S1** — bridge entity labels → `finskalp_entities`
- **TD-S2** — unified Neo4j projection (новые записи)
- **TD-C5** — shared platform v2 routes (частично: legacy demo routes сохранены с Deprecation headers)
- **TD-M1** — graph versioning auto-persist (memory + Postgres)
- **RFC-0003 ER / ingest / KG** — env-based store, mandatory path, UI

## Остаётся вне scope

- TD-C1–C4, C3 RBAC на legacy `compliance.py`
- TD-S3–S8, TD-M2–M6, TD-L1–L2
- Полный отказ от `EvidenceGraphNeo4jExporter` (read compat сохранён)
- TD-S6 full-scan bootstrap entity labels

## Тесты

```bash
uv run pytest flowsint-crypto-compliance/tests/test_platform_v2.py \
  flowsint-crypto-compliance/tests/test_platform_v2_integration.py \
  flowsint-crypto-compliance/tests/test_platform_v3_knowledge_graph.py \
  flowsint-crypto-compliance/tests/test_rfc0002_0003_debt_closure.py -q
```

## Переменные окружения

```env
FINSKALP_ENTITY_STORE=postgres   # memory | in_memory для offline
FINSKALP_FUSION_MODE=rfc0003     # legacy для RFC-0002-only fusion stages
```
