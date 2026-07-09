# Карта технического долга и архитектурных рисков

**RFC-0001 · Главы 11–12, 16** · Статус: Draft · Дата: 2026-07-08

Классификация: **C** critical · **S** significant · **M** moderate · **L** cosmetic

---

## Critical

| ID | Проблема | Evidence | Влияние |
|----|----------|----------|---------|
| TD-C1 | Нет единой сущности **Case** | `Investigation`, `ComplianceCase`, 2× Neo4j case labels | Расследование не entity-first |
| TD-C2 | **Evidence** не first-class в БД | JSONB, OsintFinding, graph in-memory | Evidence First нарушен |
| TD-C3 | `compliance.py` без RBAC | ~~Нет `require_permission`~~ — **закрыто**: `require_permission` на mutate routes | — |
| TD-C4 | Цикл пакетов core ↔ crypto-compliance | `pyproject.toml` обоих | Plugin First невозможен |
| TD-C5 | Два API gateway (5001 / 8877) | `web_server.py` + `main.py` | API First, security drift — **частично закрыто**: `platform/v2/routes.py` |

---

## Significant

| ID | Проблема | Evidence |
|----|----------|----------|
| TD-S1 | Тройной plane wallet labels | registry + entity_labels + caches — **закрыто RFC-0002 M2**: `entity_label_bridge.py` |
| TD-S2 | Два Neo4j schema для Wallet/Case | `wallet_neo4j.py` vs `neo4j_exporter.py` — **закрыто RFC-0002 M2**: unified projection + facade |
| TD-S3 | Demo stand ~91 route, token на 3 | `assert_demo_api_token` rare |
| TD-S4 | `COMPLIANCE_DEMO_MODE` bypass Postgres | `compliance.py:71+` |
| TD-S5 | Два RBAC: investigation vs compliance roles | ✅ RFC-0009 harmonized layer |
| TD-S6 | Postgres entity store full scan on init | `postgres_entity_store.py:38` |
| TD-S7 | Docker API image без COPY crypto-compliance | `flowsint-api/Dockerfile` |
| TD-S8 | Events не backbone — прямые вызовы | `compliance_events.py` optional |

---

## Moderate

| ID | Проблема |
|----|----------|
| TD-M1 | Graph memory backend без reload | **закрыто RFC-0003 Ch.6**: auto-versioning + DB snapshots |
| TD-M2 | KYT exposure только in-memory |
| TD-M3 | UI timeout logic в `app.js` |
| TD-M4 | Git deps без pin (maigret, recon*) |
| TD-M5 | networkx version split core vs compliance |
| TD-M6 | Synthetic microservices в UI |

---

## Cosmetic

| ID | Проблема |
|----|----------|
| TD-L1 | RU/EN mix в идентификаторах |
| TD-L2 | Version skew packages 0.1.0 vs 1.2.8 |

---

## Соответствие RFC-0000 (snapshot)

| Principle | Оценка |
|-----------|--------|
| Entity First | ✅ Improved (RFC-0002/0003 closure) |
| Evidence First | ⚠️ Partial |
| Explainability | ✅ Good |
| Human in the Loop | ✅ Good |
| Knowledge Graph | ✅ Improved (Postgres default, mandatory ingest, UI) |
| Event Driven | ✅ Improved (rfc0003 fusion + event subscriber ingest) |
| API First | ⚠️ Demo bypass — shared v2 routes added |
| Plugin First | ❌ Weak (cycle) |
| Modularity | ⚠️ Label duplication |
| Sovereign by Design | ✅ Good |

---

## Приоритет Volume II (рекомендации, не реализация)

1. ~~**RFC-0002** — Entity consolidation~~ ✅ M2 closed (2026-07-08)
2. ~~**RFC-0003** — Knowledge Graph + ingest~~ ✅ closed (2026-07-08)
3. **RFC-0004** — Break package cycle (compliance as plugin)
4. ~~**RFC-0005** — Unified Neo4j projection~~ ✅ merged into RFC-0002 closure
5. **RFC-0005** — Investigation Platform & Enterprise Operations ✅ [`rfc0005-completion.md`](../architecture/v2/rfc0005-completion.md)
6. **RFC-0006** — Intelligence Engine ✅ [`rfc0006-completion.md`](../architecture/v2/rfc0006-completion.md)
7. **RFC-0007** — Integration & Connectors ✅ [`rfc0007-completion.md`](../architecture/v2/rfc0007-completion.md)
8. **RFC-0008** — Enterprise Design System ✅ [`rfc0008-completion.md`](../architecture/v2/rfc0008-completion.md)
9. **RFC-0009** — RBAC Harmonization ✅ [`rfc0009-completion.md`](../architecture/v2/rfc0009-completion.md)
10. **RFC-0010** — Analyst Workspace & User Experience ✅ [`rfc0010-completion.md`](../architecture/v2/rfc0010-completion.md)
11. **RFC-0011** — Workflow & User Interaction Logic ✅ [`rfc0011-completion.md`](../architecture/v2/rfc0011-completion.md)
12. **RFC-0012** — Blockchain Intelligence Framework ✅ [`rfc0012-completion.md`](../architecture/v2/rfc0012-completion.md)
13. **RFC-0013** — Incremental Block Sync ✅ [`rfc0013-completion.md`](../architecture/v2/rfc0013-completion.md)

---

## Архитектурные риски (реестр)

| Risk | Вероятность | Impact | Mitigation today |
|------|-------------|--------|------------------|
| Prod container restart via compose merge | Medium | High | Standalone hardening only |
| Health probe timeout | Low | Medium | `/api/health/live` |
| TRON provider outage | Medium | High | Failover provider |
| Demo stand exposed on 0.0.0.0 | Medium | High | `FINSKALP_DEMO_API_TOKEN`, bind 127.0.0.1 |
| JWT user escalates via compliance.py | Medium | High | RBAC audit backlog |
