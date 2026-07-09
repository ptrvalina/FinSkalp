# RFC-0022: Enterprise Governance & Product Roadmap v2.0

**RFC-0022 · EGPR · v2.0**

| Поле | Значение |
|------|----------|
| Статус | Accepted — Implemented (2026-07-09) |
| Предшественники | [RFC-0000](RFC-0000-enterprise-constitution.md), [RFC-0021](RFC-0021-infrastructure-devops-observability.md) |
| Реализация | `platform/v2/egpr/` |
| Completion | [`rfc0022-completion.md`](../architecture/v2/rfc0022-completion.md) |
| Позиция | **Final chapter of Volume I** — Enterprise Architecture Book complete |

---

## Предисловие

EGPR — финальная глава Volume I Enterprise Architecture Book. Объединяет миссию, стратегические принципы, Architecture Board, ADR, жизненный цикл RFC, дорожную карту и критерии зрелости платформы FinSkalp v2.0.

**Управляемая эволюция архитектуры через RFC, ADR и Architecture Board.**

---

## Глава 1. Миссия

`mission.py` — миссия платформы, stakeholders, Volume I status.

## Глава 2. Стратегические принципы

10 принципов из RFC-0000 + `check_principle_compliance()` — `principles.py`.

## Глава 3. Architecture Board

Charter, quorum, review workflow stub — `architecture_board.py`.

## Глава 4. ADR Registry

In-memory ADR store (ADR-0001/0002/0003 → RFC-0002/0009/0019) — `adr_registry.py`.

## Глава 5. RFC Lifecycle

Каталог RFC-0000 through RFC-0021, stage transitions — `rfc_lifecycle.py`.

## Глава 6. Releases

Semver manifest, CHANGELOG.md link — `releases.py`.

## Глава 7. Development Standards

Code style, review, testing, security checklist — `dev_standards.py`.

## Глава 8. Technical Debt

Bridge to `docs/audit/technical-debt.md` — `tech_debt.py`.

## Глава 9. Requirements

Requirement registry linked to RFCs — `requirements.py`.

## Глава 10. Quality

Test coverage stub, build success, API stability — `quality.py`.

## Глава 11. Knowledge Management

Portal manifest (RFC, architecture, runbooks) — `knowledge.py`.

## Глава 12. Project Risks

Risk register — `project_risks.py`.

## Глава 13. Team Model

10 teams with roadmap/KPI stubs — `teams.py`.

## Глава 14. KPI Maturity

Platform KPIs (SLO reference from IDOO) — `kpi_maturity.py`.

## Глава 15. Product Roadmap

4 phases: MVP → Enterprise → Platform → National Scale — `roadmap.py`.

## Глава 16. Maturity Criteria

Auto-evaluation against completion docs — `maturity.py`.

## Глава 17. LTS Support

24-month LTS policy — `support.py`.

## Глава 18. Evolution Rules

RFC→ADR→Review→Test→Board workflow — `evolution.py`.

## Глава 19. Five-Year Vision

2031 sovereign national-scale vision — `vision.py`.

## Глава 20. Constraints

No architecture change without Board — `constraints.py`.

---

## API

| Метод | Путь |
|-------|------|
| GET | `/api/platform/v2/egpr/manifest` |
| GET | `/api/platform/v2/egpr/roadmap` |
| GET | `/api/platform/v2/egpr/rfc-catalog` |
| GET | `/api/platform/v2/egpr/adr` |
| GET | `/api/platform/v2/egpr/maturity` |
| GET | `/api/platform/v2/egpr/tech-debt` |
| GET | `/api/platform/v2/egpr/kpi` |
| POST | `/api/platform/v2/egpr/rfc/{rfc_id}/transition` |

## Celery

- `egpr_maturity_snapshot` — daily beat 86400s

## Volume I Complete

С RFC-0022 каталог Volume I (RFC-0000 through RFC-0022) завершён на 100%.
