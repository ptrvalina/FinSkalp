# RFC-0018 Explainable AI & Investigation Assistant — 100% Completion Checklist

Дата: 2026-07-09

## Архитектурная модель (Глава 1)

- ✅ Pipeline: Context → Prompt → Model → Explanation → Recommendation → Summary → Deliver
- ✅ `orchestrator.run_eia_task` — явная проводка всех стадий
- ✅ `EIAStage` enum — 7 стадий

## Типы задач (Глава 2)

- ✅ `AITaskType` — 8 типов (summary, explain_risk, describe_links, questions, report_outline, explain_changes, contradictions, data_gaps)
- ✅ `AssistantResponse`, `Citation` — unified envelope

## Движки (Главы 4–12)

- ✅ `context_engine.build_investigation_context` — multi-source read-only
- ✅ `prompt_engine.render_prompt` — versioned templates
- ✅ `explanation_engine` — explain_risk, explain_links, explain_graph_cluster
- ✅ `recommendation_engine` — requires_analyst_confirmation=True
- ✅ `summary_engine.build_investigation_brief`
- ✅ `report_assistant.build_report_outline`
- ✅ `graph_assistant.build_graph_narrative`
- ✅ `timeline_assistant.build_timeline_analysis`
- ✅ `evidence_assistant.build_evidence_summary`

## Model & Prompt Registry (Главы 13–14)

- ✅ `prompt_registry` — in-memory versioned store
- ✅ `model_registry` — DeterministicModel + OpenAICompatibleAdapter stub

## Security & Monitoring (Главы 15–16)

- ✅ `security.eia_security_manifest` — audit log, PII guard
- ✅ `monitoring.EIAMetrics`

## Constraints (Главы 7, 18)

- ✅ `constraints.eia_architectural_constraints` — no mutation, no auto_decision

## API и Celery (Главы 17, 19)

- ✅ gateway.py — 5 handlers
- ✅ routes.py — 5 endpoints
- ✅ `flowsint-core/tasks/eia.py` — `eia_warm_context_cache` beat 1200s

## UI

- ✅ `compliance-service.ts` — EIA API methods
- ✅ `compliance-page.tsx` — RFC-0018 status block (Russian)

## Тесты

- ✅ `tests/test_rfc0018_eia.py` — 9 tests (manifest, context, explain_risk, recommendations, constraints, prompts, API, report)

## Документация

- ✅ `docs/rfc/RFC-0018-explainable-ai-investigation-assistant.md`
- ✅ `docs/rfc/README.md` — RFC-0018 entry
- ✅ `docs/audit/technical-debt.md` — TD-EIA-* items
