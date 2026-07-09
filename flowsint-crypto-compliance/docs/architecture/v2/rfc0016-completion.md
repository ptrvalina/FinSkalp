# RFC-0016 Risk & Decision Engine — 100% Completion Checklist

Дата: 2026-07-09

## Архитектурная модель (Глава 1)

- ✅ Pipeline: Fact Acquisition → Normalize → Correlate → Aggregate → Scores → Rules → Explain → Deliver
- ✅ `orchestrator.run_rde_assessment` — явная проводка всех стадий
- ✅ `RDEStage` enum — 8 стадий

## Факторные группы (Глава 3)

- ✅ `FactorGroup` — blockchain, registry, osint, graph, evidence
- ✅ `factors.py` — калькуляторы per group

## Нормализация (Глава 2)

- ✅ `normalizer.normalize_signals` — read-only трансформация

## Корреляция (Глава 12)

- ✅ `correlator.correlate_signals` — 4 типа кросс-доменных корреляций

## Агрегация (Глава 3)

- ✅ `aggregator.aggregate_factors` — weighted composite score

## Confidence (Глава 6)

- ✅ `confidence.ConfidenceScore` — 5 измерений

## Risk Levels (Глава 7)

- ✅ `risk_levels.map_score_to_risk_level` — transitions

## Explainability (Глава 8)

- ✅ `explainability.build_explanation` — why/facts/rules/sources/missing

## Rules Engine (Главы 5, 13)

- ✅ `rules_engine.RulesEngine` — versioned rules, history, preview, rollback stubs
- ✅ `elevated_attention` rule

## Decision Support (Глава 9)

- ✅ `decision_support.generate_recommendations` — requires_analyst=True, auto_decision=False

## Prioritization (Глава 10)

- ✅ `prioritization.prioritize_investigation_objects`

## Temporal (Глава 11)

- ✅ `temporal.TemporalStore` — snapshots, compare, trends, spike detection

## Monitoring (Глава 14)

- ✅ `monitoring.RDEMetrics`

## Security & SDK (Главы 15–16, 19)

- ✅ `security.rde_security_manifest()`
- ✅ `sdk.rde_sdk_manifest()`

## Constraints (Глава 18)

- ✅ `constraints.rde_architectural_constraints()`

## API и Celery (Главы 17, 20)

- ✅ gateway.py — 6 handlers
- ✅ routes.py — 6 endpoints
- ✅ `flowsint-core/tasks/rde.py` — `rde_batch_reassess` beat 900s

## UI

- ✅ `compliance-service.ts` — RDE API methods
- ✅ `compliance-page.tsx` — RFC-0016 status block (Russian)

## Тесты

- ✅ `tests/test_rfc0016_rde.py` — 8+ tests
