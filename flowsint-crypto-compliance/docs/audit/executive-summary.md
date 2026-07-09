# Executive Summary — RFC-0001 Architecture Audit

**Дата:** 2026-07-08 · **Статус:** Draft (инвентаризация завершена, Volume II не начат)

---

## Что такое FinSkalp сегодня

Self-hosted платформа криптофорензики и ПОД/ФТ с **двумя HTTP-поверхностями**:

- **flowsint-api** (:5001) — production JWT API
- **regulator-stand** (:8877) — combat/demo монолит с полным FinSkalp pipeline

Ядро доменной логики — пакет **flowsint-crypto-compliance** (OSINT Scalpel, fusion, risk, отчёты). Персистенция: PostgreSQL (`compliance_*`), граф Neo4j (две схемы), Redis/Celery.

---

## Главные выводы

### 1. Функциональное ядро сильное, архитектурная целостность — слабая

Первый этап доказал жизнеспособность: live TRON, OSINT fusion, evidence preservation, institutional memory, hardening stack. Но **RFC-0000 Entity First** и **Knowledge Graph** реализованы частично.

### 2. Три критических долга

1. **Два Case** — `Investigation` vs `ComplianceCase` vs 2× Neo4j
2. **Два API** — demo и prod с разной auth и дублирующими routes
3. **Цикл пакетов** — `flowsint-core` ↔ `flowsint-crypto-compliance`

### 3. Безопасность: prod и demo живут в разных мирах

Demo hardened (SSRF, rate limit, health fix), но **RBAC gap** в `compliance.py`. Demo mutating endpoints открыты без token по умолчанию.

### 4. Производительность понятна

Bottleneck = investigate pipeline (до 300s), multi-hop fusion, sync PDF. Observability (Tempo) и hot indexes уже заложены.

### 5. Sovereign by design — сильная сторона

TRON failover, offline OFAC, self-hosted Meilisearch/Unleash/Tempo, localhost hardening.

---

## Артефакты аудита

| # | Документ | Статус |
|---|----------|--------|
| 1 | [service-catalog.md](service-catalog.md) | ✅ Draft |
| 2 | [api-catalog.md](api-catalog.md) | ✅ Draft |
| 3 | [data-model-map.md](data-model-map.md) | ✅ Draft |
| 4 | [external-integrations.md](external-integrations.md) | ✅ Draft |
| 5 | [technical-debt.md](technical-debt.md) | ✅ Draft |
| 6 | [security-report.md](security-report.md) | ✅ Draft |
| 7 | [performance-map.md](performance-map.md) | ✅ Draft |
| 8 | Карта потоков данных | ⏳ Volume II |
| 9 | Карта бизнес-процессов | ⏳ Volume II |
| 10 | Рекомендации Enterprise Architecture | ⏳ RFC-0002+ |

---

## Что делать дальше (порядок RFC)

**На этапе RFC-0001 новый функционал не пишем.**

1. Review артефактов командой / CAO
2. Утвердить **RFC-0002 Entity consolidation**
3. Утвердить **RFC-0003 Single API surface**
4. Только после — рефакторинг и Volume II

---

## Ссылки

- [RFC-0000 Constitution](../rfc/RFC-0000-enterprise-constitution.md)
- [RFC-0001 Audit charter](../rfc/RFC-0001-enterprise-architecture-audit.md)
- [HARDENING.md](../../HARDENING.md)
- [OSINT_QUALITY.md](../../OSINT_QUALITY.md)
