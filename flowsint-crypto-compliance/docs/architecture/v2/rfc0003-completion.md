# RFC-0003 — 100% completion

**Дата:** 2026-07-08 · **Статус:** Complete

## Definition of Done

| Глава RFC-0003 | Критерий | Статус |
|----------------|----------|--------|
| Ch.1–4 | Entity, Relation, Evidence models | ✅ `canonical.py` |
| Ch.5 | Mandatory ingest | ✅ `ingest_pipeline.py` |
| Ch.6 | Versioning + temporal replay | ✅ `reconstruct_graph_at`, `POST /graph/snapshot` |
| Ch.7 | Fusion RFC-0003 path | ✅ `default_fusion_pipeline()` |
| Ch.8 | Confidence model | ✅ `confidence_model.py` |
| Ch.9 | History, compare, export | ✅ compare/export/history API |
| Ch.10 | Conclusion / single core | ✅ Appendix A orchestrator |
| Appendix A | Full chain to Report | ✅ `pipeline_chain.py` + investigator |

## API (полный список)

| Метод | Путь |
|-------|------|
| GET | `/api/platform/v2/knowledge-model` |
| GET | `/api/platform/v2/pipeline-chain` |
| GET | `/api/platform/v2/entities/{id}` |
| GET | `/api/platform/v2/entities/{id}/neighbors` |
| GET | `/api/platform/v2/entities/{id}/history` |
| GET | `/api/platform/v2/entities/{id}/compare?version_a=&version_b=` |
| GET | `/api/platform/v2/relations/{id}/evidence` |
| GET | `/api/platform/v2/relations/{id}/history` |
| GET | `/api/platform/v2/graph/at?as_of=` |
| POST | `/api/platform/v2/graph/snapshot` |
| GET | `/api/platform/v2/evidence/export` |
| POST | `/api/platform/v2/ingest` |

## Production mode

```env
FINSKALP_ENTITY_STORE=postgres   # обязательно в production
FINSKALP_FUSION_MODE=rfc0003
```

При `memory` — предупреждение при старте API и demo stand.

## Тесты

```bash
uv run pytest flowsint-crypto-compliance/tests/test_rfc0003_100_percent.py -q
```

## Код

- `platform/v2/pipeline_chain.py` — Appendix A orchestrator
- `platform/v2/entity_store_mode.py` — prod vs offline policy
- `platform/v2/knowledge_store.py` — `reconstruct_graph_at`, `export_evidence_base`
- `services/finskalp_investigator.py` — end-to-end chain
