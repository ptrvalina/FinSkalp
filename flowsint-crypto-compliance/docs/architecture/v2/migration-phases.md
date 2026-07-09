# Фазы миграции v2

Не big-bang. Каждая фаза — отдельный RFC implementation + DoD.

## M1 — Foundation (RFC-0002, текущий спринт)

- [x] Канонические типы `platform/v2`
- [x] Каталог событий + `PlatformEventBus`
- [x] Postgres tables `finskalp_*`
- [x] `FusionPipeline` router (stages)
- [x] Plugin registry skeleton + Scalpel factories
- [x] Dual-write: `OsintFinding` → `finskalp_evidence` (Evidence Center)
- [x] PlatformEvent → `finskalp_platform_events`

## M2 — Knowledge unification

- [x] Entity Resolution Engine (wallet + phone + domain → Entity)
- [x] Unify `ComplianceCase` + `Investigation` → case entity
- [x] Single Neo4j projection (`Finskalp*` labels)
- [x] Close TD-C1, TD-S2 (foundation)

## M3 — Presentation consolidation

- [x] Deprecate duplicate routes on :8877 (Deprecation header)
- [x] `flowsint-api` canonical `/api/platform/v2/*`
- [x] Demo stand → thin BFF (pragmatic, not deleted)
- [x] compliance_rbac on mutating routes (TD-C3)

## M4 — Event backbone

- [x] PlatformEventSubscriber persists knowledge from events
- [x] Wire investigate, analyst confirm/reject, case open, scalpel collect
- [x] CQRS `GET /api/platform/v2/cases/{case_ref}/timeline`

## Критерий завершения v2

Аналитик открывает **одно расследование**; все источники пишут в Fusion → Knowledge; UI читает только Investigation API; audit trail = event log + evidence hashes.
