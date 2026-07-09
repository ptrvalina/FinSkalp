# RFC-0016: Risk & Decision Engine v2.0

**RFC-0016 · RDE · v2.0**

| Поле | Значение |
|------|----------|
| Статус | Accepted — Implemented (2026-07-09) |
| Предшественники | [RFC-0006](RFC-0006-intelligence-engine.md), [RFC-0012](RFC-0012-blockchain-intelligence.md), [RFC-0014](RFC-0014-intelligence-collection-framework.md), [RFC-0015](RFC-0015-compliance-registry-intelligence.md) |
| Реализация | `platform/v2/rde/` |
| Completion | [`rfc0016-completion.md`](../architecture/v2/rfc0016-completion.md) |

---

## Предисловие

RDE агрегирует сигналы из Blockchain Intelligence, OSINT (ICF), Registry (CRIF), Evidence Center и Knowledge Graph в единую оценку риска с объяснимостью и рекомендациями для аналитика.

**RDE агрегирует сигналы и объясняет — решение принимает аналитик.**

---

## Глава 1. Архитектурная модель

```
Fact Acquisition → Normalize → Correlate → Aggregate Factors
  → Calculate Scores → Rule Check → Explain → Deliver
```

Входные подсистемы: blockchain_intelligence, crif, icf, knowledge_store, evidence_center.

---

## Глава 2. Входные сигналы

Контекст `signals` dict с ключами: `blockchain_signals`, `registry_signals`, `osint_signals`, `graph_signals`, `evidence_signals`.

---

## Глава 3. Факторные группы

| Группа | Источник |
|--------|----------|
| blockchain | Blockchain Intelligence |
| registry | CRIF |
| osint | ICF |
| graph | Knowledge Store |
| evidence | Evidence Center |

---

## Глава 4. Калькуляторы факторов

`factors.py` — structured scoring per group из нормализованных сигналов.

---

## Глава 5. Rules Engine

`rules_engine.py` — декларативные версионированные IF/THEN правила.

---

## Глава 6. Confidence Model

`confidence.py` — independent_sources, quality, completeness, consistency, freshness.

---

## Глава 7. Risk Levels

`risk_levels.py` — informational → low → medium → high → critical с transition explanations.

---

## Глава 8. Explainability

`explainability.py` — why, facts, rules, sources, missing, limitations.

---

## Глава 9. Decision Support

`decision_support.py` — рекомендации (expand time range, check docs, related orgs, refresh registries). **НЕ решения.**

---

## Глава 10. Prioritization

`prioritization.py` — ранжирование объектов расследования.

---

## Глава 11. Temporal Analysis

`temporal.py` — snapshots, period compare, trends, spike detection (in-memory).

---

## Глава 12. Cross-Domain Correlation

`correlator.py` — blockchain↔docs, docs↔orgs, osint↔graph, blockchain↔graph.

---

## Глава 13. Rule History

`rules_engine.py` — history, preview, rollback stubs.

---

## Глава 14. Monitoring

`monitoring.py` — assessment_count, latency, success_rate, by_risk_level.

---

## Глава 15–16. Security & SDK

`security.py`, `sdk.py` — manifests.

---

## Глава 17. API

| Method | Path |
|--------|------|
| GET | `/api/platform/v2/rde/manifest` |
| POST | `/api/platform/v2/rde/assess` |
| GET | `/api/platform/v2/rde/rules` |
| POST | `/api/platform/v2/rde/rules/evaluate` |
| GET | `/api/platform/v2/rde/monitoring` |
| GET | `/api/platform/v2/rde/priorities?case_ref=` |

---

## Глава 18. Architectural Constraints

`constraints.py` — запрет мутации source data, KG, evidence; запрет auto_decision.

---

## Глава 19. Extensibility

SDK extension points: factor calculators, correlation rules, rules engine.

---

## Глава 20. Celery

`flowsint-core/tasks/rde.py` — `rde_batch_reassess`, beat 900s.

---

## Тесты

```powershell
cd flowsint-crypto-compliance
$env:FINSKALP_ENTITY_STORE="memory"
uv run pytest tests/test_rfc0016_rde.py -q
```
