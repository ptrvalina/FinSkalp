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
14. **RFC-0014** — Intelligence Collection Framework ✅ [`rfc0014-completion.md`](../architecture/v2/rfc0014-completion.md)
15. **RFC-0015** — Compliance & Registry Intelligence ✅ [`rfc0015-completion.md`](../architecture/v2/rfc0015-completion.md)
16. **RFC-0016** — Risk & Decision Engine ✅ [`rfc0016-completion.md`](../architecture/v2/rfc0016-completion.md)

---

## RFC-0014 / 0015 / 0016 — Production hardening backlog

Закрыто в коде (2026-07-09): `rde/signal_bridge.py` — автосбор сигналов blockchain+CRIF+KG+evidence для RDE.

| ID | Проблема | Статус | Блокер |
|----|----------|--------|--------|
| TD-RDE-1 | RDE temporal store in-memory | **Open** | Postgres schema + migration |
| TD-RDE-2 | Rules engine rollback — stub | **Open** | Persistent rule store |
| TD-RDE-3 | Live blockchain analyze → RDE без index | **Open** | API keys TronGrid/Etherscan |
| TD-RDE-4 | ML risk models | **Open** | Нет обученных моделей / ONNX |
| TD-ICF-1 | Live collectors не вызывают ICF orchestrator | **Open** | Celery refactor |
| TD-ICF-2 | OCR documents/images — stub | **Open** | Tesseract/cloud OCR |
| TD-CRIF-1 | Реальные госреестры РФ (ЕГРЮЛ, ЦБ) | **Open** | API-доступ регулятора |
| TD-CRIF-2 | Sanctions list — demo OFAC subset | **Open** | Лицензия OpenSanctions / FIU feed |
| TD-CRIF-3 | Registry cache/monitor in-memory | **Open** | Postgres + Redis |
| TD-CRIF-4 | Change monitoring webhook → analyst | **Open** | Notification channel (email/Slack) |
| TD-ECCF-1 | ECCF repository in-memory only | **Open** | Postgres WORM storage + migration |
| TD-ECCF-2 | Legal archive — no cold storage | **Open** | S3 Glacier / tape archive integration |
| TD-ECCF-3 | Audit trail not replicated | **Open** | Append-only log shipping (WORM bucket) |
| TD-ECCF-4 | Digital signatures on evidence packages | **Open** | GOST/RFC3161 timestamping service |
| TD-ECCF-5 | Cross-tenant evidence isolation audit | **Open** | Row-level security + penetration test |
| TD-EIA-1 | Real LLM API keys (OpenAI/Anthropic) | **Open** | API keys + HTTP client integration |
| TD-EIA-2 | Streaming SSE responses | **Open** | FastAPI SSE endpoint + frontend consumer |
| TD-EIA-3 | Fine-tuned domain models | **Open** | Training data + ONNX/GGUF deployment |
| TD-EIA-4 | Context cache — in-memory only | **Open** | Redis cache + TTL policy |
| TD-EIA-5 | Analyst history — stub | **Open** | analyst_workspace integration |
| TD-INT-1 | E2E: ICF→CRIF→RDE→Workspace в одном кейсе | **Partial** | `test_rde_auto_acquires_subsystem_signals` |
| TD-INT-2 | Package cycle core ↔ crypto-compliance | **Open** | RFC-0004 plugin extraction |


## Архитектурные риски (реестр)

| Risk | Вероятность | Impact | Mitigation today |
|------|-------------|--------|------------------|
| Prod container restart via compose merge | Medium | High | Standalone hardening only |
| Health probe timeout | Low | Medium | `/api/health/live` |
| TRON provider outage | Medium | High | Failover provider |
| Demo stand exposed on 0.0.0.0 | Medium | High | `FINSKALP_DEMO_API_TOKEN`, bind 127.0.0.1 |
| JWT user escalates via compliance.py | Medium | High | RBAC audit backlog |
