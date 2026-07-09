# FinSkalp Architecture v2

Целевая архитектура второго поколения ([RFC-0002](../rfc/RFC-0002-enterprise-architecture.md)).

## Документы

| Файл | Содержание |
|------|------------|
| [layers-and-domains.md](layers-and-domains.md) | 6 уровней + 7 DDD-доменов |
| [canonical-model.md](canonical-model.md) | Entity, Evidence, Events |
| [event-catalog.md](event-catalog.md) | Каталог событий v2 |
| [domain-boundaries.md](domain-boundaries.md) | As-is → to-be маппинг модулей |
| [migration-phases.md](migration-phases.md) | Фазы M1–M4 |
| [data-flow-map.md](data-flow-map.md) | Потоки данных L1–L6 |
| [business-process-map.md](business-process-map.md) | Бизнес-процессы расследования |

## Код

```
flowsint_crypto_compliance/platform/v2/
  canonical.py      # канонические типы
  events.py         # PlatformEvent + EventType
  event_bus.py      # адаптер ComplianceEventBus + Postgres
  contracts.py      # Protocol интерфейсы доменов
  plugin_registry.py
  fusion_pipeline.py
  evidence_center.py
  entity_resolution.py
  knowledge_store.py
  investigation_workspace.py
  neo4j_projection.py
  event_subscriber.py
  gateway.py
```

## Принцип внедрения

**Strangler fig:** новые пути пишутся через `platform/v2`; legacy (`web_server`, прямые imports) мигрируют по фазам без big bang.
