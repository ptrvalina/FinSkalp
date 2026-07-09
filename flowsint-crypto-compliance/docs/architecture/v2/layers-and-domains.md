# Шесть уровней и семь доменов

## Layer stack

```
┌─────────────────────────────────────────────────────────┐
│ L6 Presentation — UI, REST, GraphQL, CLI, PDF/Excel   │
├─────────────────────────────────────────────────────────┤
│ L5 Investigation — Case, Evidence, Workflow, Audit      │
├─────────────────────────────────────────────────────────┤
│ L4 Intelligence — Risk, Attribution, Timeline, AI       │
├─────────────────────────────────────────────────────────┤
│ L3 Knowledge — Entity Graph, versions, relations        │
├─────────────────────────────────────────────────────────┤
│ L2 Fusion — validate, normalize, dedup, enrich, publish │
├─────────────────────────────────────────────────────────┤
│ L1 Acquisition — blockchain, OSINT, OCR, registry, …    │
└─────────────────────────────────────────────────────────┘
         ▲ events only ▲
```

## DDD domains → layers

| Domain | Layer | As-is modules (RFC-0001) |
|--------|-------|--------------------------|
| **Acquisition** | L1 | `osint_core/scalpel/`, `live_collectors.py`, `chains/`, OCR |
| **Fusion** | L2 | `osint/fusion_confidence.py`, `multihop_fusion.py`, `engine/exposure_engine.py` |
| **Knowledge** | L3 | Neo4j exporters, `evidence_graph.py` → `finskalp_entities` |
| **Analytics** | L4 | `attribution/`, `detection/`, `ml/`, `engine/xgboost_risk.py` |
| **Investigation** | L5 | `ComplianceCase`, inbox, workflow, `finskalp_investigator.py` |
| **Presentation** | L6 | `flowsint-api`, `demo/web_server.py`, `flowsint-app` |
| **Platform** | cross | auth, tracing, events, feature flags, idempotency |

## Правила потока данных

1. L1 публикует `RawDataAcquired` / domain-specific acquisition events.
2. L2 потребляет acquisition events → выдаёт `FusedIntelligenceReady`.
3. L3 материализует Entity/Relation/Evidence.
4. L4 читает только Knowledge Graph (+ read models).
5. L5 привязывает Evidence к Case, workflow, audit.
6. L6 — read-only к Investigation + Analytics projections.

**Запрещено:** Scalpel → напрямую PDF; Risk → TronGrid; UI → Postgres чужого домена.
