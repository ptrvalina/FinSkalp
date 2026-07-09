# Business process map — RFC-0002

## Процесс: открытие расследования

| Шаг | Актор | Действие | v2 компонент |
|-----|-------|----------|--------------|
| 1 | Аналитик | Создаёт дело `case_ref` | `POST /api/platform/v2/cases` или `POST /api/compliance/cases` |
| 2 | Platform | Bridge `ComplianceCase` → case Entity | `InvestigationWorkspace.open_case` |
| 3 | Event bus | `CaseOpened` → Postgres + subscriber | `PlatformEventBus` |
| 4 | Knowledge | Upsert `finskalp_entities` type=case | `KnowledgeGraphStore` |
| 5 | Graph | Neo4j `FinskalpCase` node | `Neo4jUnifiedProjection` |

## Процесс: расследование адреса

| Шаг | Актор | Действие | v2 компонент |
|-----|-------|----------|--------------|
| 1 | Аналитик | `POST /api/platform/v2/investigate` | flowsint-api gateway |
| 2 | Investigator | OSINT + on-chain screening | `FinSkalpInvestigator` |
| 3 | Fusion | 7-stage pipeline | `FusionPipeline` |
| 4 | Workspace | Link wallet Entity to case | `InvestigationWorkspace.attach_investigation` |
| 5 | Evidence | Dual-write OSINT findings | `EvidenceCenter` + `osint_findings` |
| 6 | Analytics | Risk score event | `RiskUpdated` |

## Процесс: сбор OSINT (Scalpel)

| Шаг | Действие | Event |
|-----|----------|-------|
| 1 | Выбор коллекторов из plugin registry | `scalpel.*` factories |
| 2 | `POST /api/platform/v2/scalpel/collect` | — |
| 3 | Extract entities (domain, phone, email, …) | `OsintMentionFound` per mention |
| 4 | Subscriber persists entity + evidence | `KnowledgeGraphStore` |

## Процесс: ревью аналитика (атрибуция)

| Шаг | Действие | Event |
|-----|----------|-------|
| 1 | Confirm / reject label | `POST /api/platform/v2/attribution/{confirm\|reject}` |
| 2 | Update entity label store | `postgres_entity_store` |
| 3 | Platform event | `ReviewSubmitted` |
| 4 | Knowledge projection | wallet Entity + `analyst_label` attribute |

## Процесс: аудит и timeline

| Шаг | Действие | Store |
|-----|----------|-------|
| 1 | Любое значимое изменение | `PlatformEventBus.publish` |
| 2 | Append-only log | `finskalp_platform_events` |
| 3 | UI timeline | `GET /api/platform/v2/cases/{case_ref}/timeline` |

## RBAC (TD-C3)

| Permission | Операции |
|------------|----------|
| `case:read` | timeline, list cases |
| `case:create` | open case |
| `case:transition` | fuse, bank feeds, hub |
| `batch:screen` | investigate, scalpel, wallet screen |
| `watchlist:manage` | registry import |

Enforcement: `flowsint-api` `compliance.py` mutating routes via `require_permission`.

## Deprecation (M3)

Demo stand routes (`:8877`) возвращают заголовки:

- `Deprecation: true`
- `Link: </api/platform/v2/...>; rel="successor-version"`

Канонический gateway: `flowsint-api` `/api/platform/v2/*`.
