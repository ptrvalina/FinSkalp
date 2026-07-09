# Каноническая модель данных v2

## Entity (центральная сущность)

```text
Entity
├── id: UUID
├── tenant_id: UUID
├── entity_type: EntityType
├── canonical_key: str          # нормализованный ключ (address, email, …)
├── display_name: str
├── version: int                # optimistic concurrency
└── attributes[]: EntityAttribute
```

### EntityType (RFC-0000 + extensions)

`person`, `organization`, `wallet`, `transaction`, `smart_contract`, `exchange`, `bank`, `document`, `evidence`, `case`, `phone`, `email`, `domain`, `ip_address`, `sanction_record`, `registry_record`

## EntityAttribute

| Поле | Описание |
|------|----------|
| key | `risk_score`, `chain`, `label`, … |
| value | JSON-serializable |
| source | collector / analyst / fusion |
| confidence | 0..1 |
| valid_from | timestamp |

## EntityRelation

| Поле | Описание |
|------|----------|
| from_entity_id, to_entity_id | UUID |
| relation_type | `owns`, `sent_to`, `mentioned_with`, `same_as`, … |
| confidence | 0..1 |
| evidence_ids | UUID[] |

## Evidence (Evidence Center)

| Поле | Описание |
|------|----------|
| id | UUID |
| tenant_id, case_id | scope |
| source_type | explorer_tag, darknet_index, … |
| content_hash | SHA-256 |
| snapshot_uri | preserved artifact |
| discovered_at | ISO timestamp |
| trust_level | admiralty-inspired 0..1 |
| payload | JSON metadata |

## PlatformEvent (event store)

| Поле | Описание |
|------|----------|
| id | UUID |
| event_type | из каталога |
| schema_version | semver string |
| occurred_at | timestamp |
| source | service name |
| actor | user/system id |
| investigation_id | optional context |
| payload | JSON |

## Postgres tables (migration `n6o7p8q9r0s1`)

- `finskalp_entities`
- `finskalp_entity_attributes`
- `finskalp_entity_relations`
- `finskalp_evidence`
- `finskalp_platform_events`

## Маппинг legacy → canonical

| Legacy | Canonical |
|--------|-----------|
| `ComplianceCase` | Entity type=`case` + investigation projection |
| `ComplianceEntityLabel` | Entity type=`wallet` + attribute `attribution` |
| `OsintFinding` | Evidence row + Entity link |
| `Investigation` (core) | Investigation workspace id → case entity |
| Neo4j `Wallet` / `ComplianceWallet` | Graph projection of `wallet` entities |

Имплементация типов: `platform/v2/canonical.py`
