# RFC-0005 Investigation Platform — 100% Completion Checklist

Дата: 2026-07-08

## Investigation First (Глава 1)

- ✅ `InvestigationPlatformService` — расследование как центральный объект
- ✅ Workspace объединяет цели, доказательства, timeline, рекомендации

## Case Management (Глава 2)

- ✅ `case_workflow.py` — RFC-0005 lifecycle (7 стадий + `internal_review`)
- ✅ ComplianceCase: id, статус, приоритет, владелец, assignee, SLA, audit
- ✅ `GET /investigations/{case_ref}/workspace`

## Evidence Center (Глава 3)

- ✅ Регистрация доказательств — `POST /investigations/{case_ref}/evidence`
- ✅ Список — `GET /investigations/{case_ref}/evidence`
- ✅ Смена статуса (без удаления) — `PATCH /evidence/{id}/status`
- ✅ content_hash, trust, status_history в payload

## Timeline (Глава 4)

- ✅ `GET /cases/{case_ref}/timeline` + temporal replay filter в service
- ✅ Источники: platform events, fusion, intelligence, audit

## Workspace (Глава 5)

- ✅ 10 панелей в manifest и workspace view
- ✅ UI: compliance-service API + investigation components

## Explainable Investigation (Глава 6)

- ✅ `GET /investigations/{case_ref}/explain/{entity_id}`

## Collaboration (Глава 7)

- ✅ ComplianceCaseComment, assignee, audit log (compliance API)
- ✅ collaboration block в workspace

## Reports (Глава 8)

- ✅ 8 типов отчётов в manifest
- ✅ `/api/compliance/cases/{id}/report.json|pdf|xlsx|fz115`

## Security (Глава 9)

- ✅ compliance_rbac, audit log, evidence integrity (hash)
- ✅ ABAC/MFA — ready flags в manifest

## Operations (Глава 10–11)

- ✅ `GET /operations/manifest`
- ✅ Prometheus metrics, OTLP tracing, Grafana dashboards

## Platform as Product (Глава 12–13)

- ✅ Единая модель данных, API, тесты, документация
- ✅ Release cycle в operations manifest

## Тесты

- ✅ `tests/test_rfc0005_investigation_platform.py`

## UI

- ✅ `complianceService.getInvestigationWorkspace`, `listInvestigationEvidence`, `getCaseTimeline`
- ✅ `InvestigationWorkspaceSection` на `/dashboard/investigations/$id` — связь с кейсом комплаенса, доказательства, хронология
- ✅ `InvestigationContextProvider` в `flowsint-app/src/main.tsx`
