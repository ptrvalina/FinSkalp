# RFC-0015: Compliance & Registry Intelligence Framework v2.0

**RFC-0015 · CRIF · v2.0**

| Поле | Значение |
|------|----------|
| Статус | Accepted — Implemented (2026-07-09) |
| Предшественники | [RFC-0007](RFC-0007-integration-connectors.md), [RFC-0003](RFC-0003-unified-data-model-knowledge-graph.md) |
| Реализация | `platform/v2/crif/` |
| Completion | [`rfc0015-completion.md`](../architecture/v2/rfc0015-completion.md) |

---

## Предисловие

Комплаенс-расследования требуют проверки организаций по государственным реестрам, санкционным спискам, лицензиям и корпоративным справочникам. CRIF обеспечивает единый конвейер от источника реестра до рабочего места аналитика.

Реестр — **поставщик юридических фактов**, а не готовых комплаенс-выводов.

---

## Глава 1. Архитектурная модель

```
Registry Source → Registry Connector → Normalizer → Schema Validator
  → Entity Resolver → Evidence Generator → Knowledge Graph
  → Risk Engine → Investigation Workspace
```

Каждый уровень выполняет строго определённую функцию. Прямая мутация KG, Risk и Investigation запрещена.

---

## Глава 2. Канонические сущности

Organization, License, RegistryRecord, SanctionEntry, Country, Jurisdiction, BeneficialOwner, Regulator, ComplianceRule.

---

## Глава 3. Категории источников реестров

| Категория | Описание |
|-----------|----------|
| government | Государственные реестры |
| sanctions | Санкционные списки (OFAC и др.) |
| licenses | VASP и финансовые лицензии |
| corporate | Корпоративные справочники |

---

## Глава 4. Registry Connector

`RegistryConnector` оборачивает RFC-0007 connector: connect → authenticate → collect → normalize → validate → publish → shutdown.

---

## Глава 5. Нормализация и валидация схемы

- `normalizer.RegistryNormalizer` — канонические типы CRIF
- `schema_validator.RegistrySchemaValidator` — обязательные поля и confidence

---

## Глава 6. Проверки организаций

`compliance_checks.run_organization_checks` — exists, registration, licenses, restrictions, status changes, cross-source matches.

---

## Глава 7. Санкционный скрининг

`sanctions.screen_sanctions` — exact / fuzzy / transliteration. Probable matches всегда `requires_analyst_confirmation=True`.

---

## Глава 8. История изменений

`change_history.ChangeHistoryStore` — in-memory timeline per organization key.

---

## Глава 9. Декларативные правила

`rules_engine.RulesEngine` — версионированные IF/THEN правила, например `license_lost + active_ops → ComplianceEvent`.

---

## Глава 10. Юрисдикционная разведка

`jurisdiction.resolve_jurisdiction` — метаданные регулятора, FATF, risk tier.

---

## Глава 11. Risk Bridge

`risk_bridge.emit_risk_compliance_events` — публикует события для Risk Engine, **не мутирует risk score**.

---

## Глава 12. Evidence Generator

Поля: id, source, discovered_at, acquisition_method, content_hash, version, trust_level, registry_source, jurisdiction.

---

## Глава 13. Мониторинг изменений

`monitor.RegistryMonitor` — periodic change detection + event publish stubs.

---

## Глава 14. Кэширование

`cache.RegistryCache` — TTL cache для immutable registry data.

---

## Глава 15–16. Безопасность и SDK

- `security.crif_security_manifest()`
- `sdk.crif_sdk_manifest()` extends RFC-0007

---

## Глава 17. Метрики

`metrics.CRIFMetrics` — latency, requests, checks, sanctions, rules fired.

---

## Глава 18. Архитектурные ограничения

RegistryConnector **запрещено**: изменять Graph, Risk, Investigation напрямую; обходить Entity Resolution.

---

## Глава 19–20. API и Celery

| Endpoint | Метод |
|----------|-------|
| `/crif/manifest` | GET |
| `/crif/check` | POST |
| `/crif/sanctions/screen` | POST |
| `/crif/rules` | GET |
| `/crif/rules/evaluate` | POST |
| `/crif/metrics` | GET |
| `/crif/history/{entity_key}` | GET |

Celery: `crif_sync_registries` — beat каждые 600s.

---

## Реестровые коннекторы

| connector_id | Категория |
|--------------|-----------|
| registry.ofac | sanctions |
| registry.sovereign | government |
| registry.cis_vasp | licenses |
| registry.corporate | corporate |
