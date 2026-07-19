# Analyst Workflow — STR as Mission

## Pipeline (Human Labels)

```
НОВЫЙ STR → СКОРИНГ → OSINT FUSION → ГРАФ СВЯЗЕЙ →
ГИПОТЕЗЫ → ДОКАЗАТЕЛЬСТВА → ОЦЕНКА РИСКА →
РЕКОМЕНДАЦИЯ → SAR / ОТЧЁТ
```

## Mission Mapping

| Stage | Strip field | Primary surface |
|-------|-------------|-----------------|
| Ingress | QUEUE | Command Alpha |
| Triage | THREAT | Mission strip |
| Fusion | INTELLIGENCE | Live feed + graph pulse |
| Analysis | OBJECTIVE | Graph center |
| Hypothesis | HYPOTHESES | MIO cards |
| Evidence | EVIDENCE Q | Left timeline + bottom dock |
| Decision | RECOMMENDATIONS | MIO execute cards |
| Filing | STATUS | Strip + reports dock |

## Workflow API

- `getWorkflowStats()` — national pipeline counts
- `getWorkflowRecommendations(caseRef)` — MIO action source
- `transitionCase(caseId, status)` — execute from MIO card (existing API)

## Not a Form

Analyst never fills wizard steps. Pipeline progress shows as **mission strip STATUS** + graph enrichment over time. `fuseCase` triggered from MIO card, not modal wizard.

## Collaboration

`getAnalystWorkspaceState().collaboration` — activity in timeline, not chat thread.

## SLA

`due_at`, `sla_breached` from case — strip cell with countdown (`sla-countdown` pattern from enterprise, restyled fusion).

## Success Criteria

Analyst completes STR without leaving investigation workspace except for legacy report PDF download.
