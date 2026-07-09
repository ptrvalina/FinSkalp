# RFC-0018: Explainable AI & Investigation Assistant v2.0

**RFC-0018 · EIA · v2.0**

| Поле | Значение |
|------|----------|
| Статус | Accepted — Implemented (2026-07-09) |
| Предшественники | [RFC-0010](RFC-0010-analyst-workspace.md), [RFC-0011](RFC-0011-workflow-user-interaction.md), [RFC-0016](RFC-0016-risk-decision-engine.md), [RFC-0017](RFC-0017-evidence-chain-of-custody.md) |
| Реализация | `platform/v2/eia/` |
| Completion | [`rfc0018-completion.md`](../architecture/v2/rfc0018-completion.md) |

---

## Предисловие

EIA — ассистент расследования с объяснимым ИИ. Координирует движки контекста, промптов, объяснений, рекомендаций, резюме и отчётов.

**EIA объясняет и рекомендует — решение принимает аналитик.**

Human-in-the-loop: нет автоматических решений, нет мутации KG/evidence/risk.

---

## Глава 1. Архитектурная модель

```
Context → Prompt → Model → Explanation → Recommendation → Summary → Deliver
```

Входные подсистемы: rde, eccf, knowledge_store, analyst_workspace, workflow, intelligence_engine.

---

## Глава 2. Типы задач (AITaskType)

| Тип | Назначение |
|-----|------------|
| summary | Краткое резюме расследования |
| explain_risk | Объяснение уровня риска |
| describe_links | Описание связей в графе |
| questions | Открытые вопросы |
| report_outline | Черновик структуры отчёта |
| explain_changes | Объяснение изменений (хронология) |
| contradictions | Анализ противоречий |
| data_gaps | Пробелы в данных |

---

## Глава 3. Типы ответа

`AssistantResponse` — narrative_ru, citations (с evidence_id), recommendations, confidence, limitations, requires_analyst_confirmation.

---

## Глава 4. Context Engine

`build_investigation_context(case_ref, entity_keys)` — case, KG neighbors, timeline, evidence, RDE assess, analyst history stub.

---

## Глава 5. Explanation Engine

`explain_risk`, `explain_links`, `explain_graph_cluster` — с evidence_ids, confidence, limitations.

---

## Глава 6. Recommendation Engine

Рекомендации с объяснениями. `requires_analyst_confirmation=True` для всех.

---

## Глава 7. Ограничения

`constraints.eia_architectural_constraints()` — запрет мутации KG/evidence/risk, auto_decision.

---

## Глава 8. Summary Engine

`build_investigation_brief()` — краткое резюме дела.

---

## Глава 9. Graph Assistant

Нарративы графа связей.

---

## Глава 10. Timeline Assistant

Анализ хронологии и изменений.

---

## Глава 11. Evidence Assistant

Только верифицированные доказательства + маркировка гипотез.

---

## Глава 12. Report Assistant

Черновик структуры отчёта + список материалов + открытые вопросы.

---

## Глава 13. Prompt Registry

Версионированные шаблоны промптов (in-memory). `render_prompt(task_type, context)`.

---

## Глава 14. Model Registry

`DeterministicModel` (stub) + `OpenAICompatibleAdapter` (stub, TD-EIA-1).

---

## Глава 15. Security

Audit log, PII guard, prompt injection guard.

---

## Глава 16. Monitoring

`EIAMetrics` — task_count, latency, cache hits/misses, by_task_type.

---

## Глава 17. API

| Endpoint | Метод |
|----------|-------|
| `/eia/manifest` | GET |
| `/eia/assist` | POST |
| `/eia/context` | GET |
| `/eia/prompts` | GET |
| `/eia/monitoring` | GET |

---

## Глава 18. Architectural Constraints

Read-only subsystems. Forbidden: mutate_knowledge_graph, mutate_evidence, mutate_risk_score, auto_decision.

---

## Глава 19. Celery

`eia_warm_context_cache` — beat 1200s, optional cache warming.

---

## Глава 20. UI

`compliance-service.ts` + `compliance-page.tsx` — RFC-0018 status block (Russian).
