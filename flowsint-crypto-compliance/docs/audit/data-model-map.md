# Схема моделей данных

**RFC-0001 · Глава 10** · Статус: Draft · Дата: 2026-07-08

Анализ только — **изменения моделей запрещены** на этапе RFC-0001.

---

## 1. Маппинг на RFC-0000 Entity

| RFC-0000 Entity | Где существует сегодня | Зрелость |
|-----------------|------------------------|----------|
| **Case** | `Investigation`, `ComplianceCase`, Neo4j `ComplianceCase`/`FinSkalpCase`, demo inbox | Фрагментирован |
| **Wallet** | `CryptoWallet` (types), `ComplianceWallet`/`Wallet` (Neo4j), screening JSONB | Частично |
| **Person** | `Profile`, `ComplianceSubject`, `Individual` (types) | Нет единой таблицы |
| **Organization** | `Organization` (types), graph nodes | Только types |
| **Evidence** | `OsintFinding`, `EvidenceGraph`, audit log, PDF, fusion JSONB | Нет таблицы Evidence |
| **Registry Record** | `ComplianceRegistryLabel`, `SovereignRiskLabel` | Дублирование |
| **Sanction Record** | OFAC/OpenSanctions в labels + collectors | В labels |
| **Bank** | `ComplianceBankFeed`, `BankRegulatorFeed` | OK |
| **Exchange** | `CompliancePlatform`, VASP registry JSON | OK |
| **Blockchain Transaction** | `CryptoWalletTransaction`, fusion graph edges | В JSONB/graph |
| **Phone / Email / Domain** | OSINT extraction, `OsintFinding.entity_type` | Нет first-class |
| **Document** | OCR output, report artifacts | Файлы, не entity |
| **Smart Contract** | Частично в EVM screening | Нет модели |

---

## 2. PostgreSQL — compliance (`db_models.py`)

| Таблица | Назначение |
|---------|------------|
| `compliance_cases` | Дело ПОД/ФТ, `fusion_result` JSONB |
| `compliance_case_comments` | Комментарии аналитика |
| `compliance_user_roles` | RBAC compliance |
| `compliance_batch_screen_jobs` | Async batch KYT |
| `compliance_watchlist_subscriptions` | Watchlist адресов |
| `compliance_webhook_endpoints` | Bank webhooks |
| `compliance_bank_feeds` | Банковские STR |
| `compliance_registry_labels` | Суверенный реестр |
| `compliance_entity_labels` | Атрибуция кошельков |
| `compliance_attribution_sync_state` | Курсор OFAC/OSINT sync |
| `compliance_fusion_runs` | Async fusion runs |
| `compliance_audit_log` | Append-only audit |
| `compliance_read_snapshots` | CQRS dashboard |
| `osint_source_reliability` | Admiralty scoring |
| `osint_findings` | Institutional memory |
| `compliance_graph_views` | UI camera state |

**Миграции:** `flowsint-api/alembic/versions/e7f8a9b0c1d2_*` … `m5n6o7p8q9r0_*`

---

## 3. PostgreSQL — platform core (`flowsint_core/core/models.py`)

| Таблица | Назначение |
|---------|------------|
| `profiles` | Пользователь (Person) |
| `investigations` | Рабочее пространство OSINT |
| `investigation_user_roles` | RBAC investigation |
| `sketches` | Canvas графа |
| `scans`, `logs` | Enricher runs |
| `analyses`, `chats` | Analyst + AI |
| `flows` | Workflow definitions |
| `keys` | Encrypted API keys |
| `custom_types`, `enricher_templates` | Extensibility |

**Связь:** `ComplianceCase.investigation_id` → `investigations.id` (опциональная)

---

## 4. Neo4j — две проекции

### A. Sketch graph (platform)

- Scope: `sketch_id`
- Repo: `flowsint_core/core/graph/repository.py`

### B. Compliance graph (FinSkalp)

| Label | RFC Entity | Файл |
|-------|------------|------|
| `Wallet` / `ComplianceWallet` | Wallet | `wallet_neo4j.py`, `neo4j_exporter.py` |
| `FinSkalpCase` / `ComplianceCase` | Case | оба файла |
| `ComplianceOsintMention` | Evidence | `neo4j_exporter.py` |
| `ComplianceSubject` | Person | `neo4j_exporter.py` |

**Проблема:** два label-set для Wallet и Case — см. TD-S2.

---

## 5. In-memory stores

| Store | Файл | RFC entity |
|-------|------|------------|
| `LabelCache` | `storage/label_cache.py` | Registry Record |
| `EntityLabelStore` | `attribution/entity_label_store.py` | Wallet labels |
| `EvidenceGraph` | `osint_core/evidence_graph.py` | Evidence |
| `FusionGraph` | `osint_core/multihop_fusion.py` | Wallet graph |
| `OperationsCenter` | `demo/operations_center.py` | Case (demo inbox) |
| `live_cache` | `osint_core/live_cache.py` | HTTP cache |

---

## 6. Дублирование (карта)

```
Case ────── Investigation (PG)
         └── ComplianceCase (PG)
         └── FinSkalpCase / ComplianceCase (Neo4j)
         └── OperationsCenter alerts (memory)

Wallet labels ── compliance_registry_labels
              └── compliance_entity_labels
              └── LabelCache / EntityLabelStore (memory)
              └── fusion_result JSONB

Evidence ──── OsintFinding (PG)
          └── EvidenceGraph (memory)
          └── ComplianceAuditLog
          └── Report PDFs / preserved snapshots
```

---

## 7. Кандидаты в Knowledge Graph (Volume II)

Без изменения текущих таблиц — **каноническая модель**:

1. `Entity` (id, type, tenant_id)
2. `EntityAttribute` (key, value, provenance)
3. `EntityRelation` (from, to, type, confidence, evidence_ids)
4. `Evidence` (id, source_type, hash, snapshot_uri, case_id)

Существующие таблицы → **projections** на Entity, не замена в одном релизе.

---

## Первоисточник

`flowsint-crypto-compliance/src/flowsint_crypto_compliance/storage/db_models.py`
