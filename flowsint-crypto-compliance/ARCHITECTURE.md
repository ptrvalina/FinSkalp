# Архитектура OSINT-ядра: свой движок + мировые базы + банки через регулятора

## Цель

Максимальное покрытие **РФ и СНГ** (серая + чёрная зона) при дополнении **международными KYT-базами** через интегратора — без зависимости от западного KYT как единственного источника истины.

## Слои системы

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ИСТОЧНИКИ ДАННЫХ                                 │
├──────────────────┬──────────────────┬──────────────────┬────────────────┤
│ Банки →          │ Лицензированные  │ Контрольные      │ International  │
│ Регулятор (hub)  │ VASP / площадки  │ закупки          │ KYT bulk/API   │
│ BankRegulatorFeed│ LicensedPlatform │ ControlPurchase  │ IntlKYTLabel   │
└────────┬─────────┴────────┬─────────┴────────┬─────────┴───────┬────────┘
         │                  │                  │                 │
         └──────────────────┴──────────────────┴─────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │      IngestPipeline           │
                    │  bank_regulator.py            │
                    │  international_kyt.py         │
                    │  pipeline.py                  │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │   EvidenceGraph +             │
                    │   EntityResolver              │
                    │   (сильная склейка узлов)     │
                    └───────────────┬───────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │ ClusterEngine   │  │ SovereignAttributor│  │ LabelCache      │
    │ RegionProfiler  │  │ CorridorAnalyzer   │  │ (мир. базы)     │
    │ BlackZone       │  │                    │  │                 │
    └────────┬────────┘  └────────┬───────────┘  └────────┬────────┘
             │                    │                       │
             └────────────────────┼───────────────────────┘
                                  ▼
                    ┌───────────────────────────────┐
                    │      MergeEngine              │
                    │  domestic > international     │
                    │  disputed KYT не перезаписывает│
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │   OSINTFusionEngine           │
                    │   → FusedAttribution          │
                    │   → FiatCryptoBridge          │
                    │   → LinkageScore              │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │   Flowsint Neo4j Graph        │
                    │   Enrichers / Case UI         │
                    └───────────────────────────────┘
```

## Сильная склейка данных (ключевая идея)

Один адрес связывается **не одной меткой**, а цепочкой доказательств:

```
Bank (Sber) ──REPORTS_SUBJECT──► Subject ──SUBJECT_OWNS_WALLET──► Wallet
     │                                                              ▲
     └──INFERRED_BANK_CRYPTO (amount match + region)────────────────┘
     │                                                              │
Platform (LocalVASP) ──PLATFORM_ADDRESS────────────────────────────┘
     │
KYT (Chainalysis via bulk) ──LABELS_WALLET──► Wallet
     │
ControlPurchase ──GROUNDED_WALLET──► Wallet (confidence = 1.0)
```

**LinkScorer** считает `linkage_strength` 0..1 по сигналам:
- прямой адрес в банковском STR
- совпадение суммы fiat
- совпадение региона
- цепочка subject
- platform bridge

## Правила merge (MergeEngine)

| Приоритет | Источник | Вес |
|-----------|----------|-----|
| 1 | Control purchase | 1.0 |
| 2 | Bank regulator hub | 0.95 |
| 3 | FIU / bank alert | 0.92–0.93 |
| 4 | Licensed VASP | 0.90 |
| 5 | Blockchain heuristics | 0.70 |
| 6 | International KYT | 0.55 |

- **RU/CIS регион** из domestic всегда якорит вывод
- **Disputed KYT** не перезаписывает sovereign label
- **Согласие** sovereign + KYT → +confidence

## Банки через госрегулятора

### Сейчас (MVP)
- `FileBankRegulatorConnector` — JSONL выгрузка из хаба регулятора
- `RegulatorAPIConnector` — stub под будущий API

### Поток
1. Банк отправляет STR/CTR в **хаб регулятора** (не напрямую в OSINT)
2. Хаб нормализует → `BankRegulatorFeed`
3. OSINT ядро забирает feed + склеивает с crypto

### Поля для сильной связки
- `payment_reference` — хэш назначения платежа
- `linked_crypto_address` — если банк уже знает адрес
- `subject_id` — псевдонимизированный субъект
- `amount` + `observed_at` — корреляция с on-chain

## International KYT (мировые базы)

### Ingest
- `parse_kyt_jsonl` / `parse_kyt_csv` — bulk snapshot от интегратора
- `LabelCache` — локальное хранение, air-gap friendly
- Периодическое обновление (daily/weekly)

### Не ground truth
- `evidence: international_kyt:chainalysis:Binance`
- `supplemental` — дополняет, не заменяет domestic

## Модули

| Путь | Назначение |
|------|------------|
| `osint_core/evidence_graph.py` | Граф доказательств |
| `osint_core/entity_resolver.py` | Склейка сущностей |
| `osint_core/link_scorer.py` | Bank↔crypto score |
| `osint_core/merge_engine.py` | Sovereign + KYT merge |
| `osint_core/fusion_engine.py` | **Главный оркестратор** |
| `ingestion/pipeline.py` | Единый ingest кейса |
| `ingestion/bank_regulator.py` | Коннектор банков |
| `ingestion/international_kyt.py` | Парсер мир. баз |
| `storage/label_cache.py` | Кэш KYT labels |

## Типы Flowsint

- `BankRegulatorFeed` — сигнал банка через регулятора
- `InternationalKYTLabel` — запись мировой базы
- `FusedAttribution` — **итоговый результат** для аналитика

## Enrichers

| Enricher | Выход |
|----------|-------|
| `wallet_to_fused_attribution` | FusedAttribution |
| `fiat_alert_to_crypto_bridge` | FiatCryptoBridge |
| `wallet_to_cluster_profile` | CryptoCluster |

## Пример кейса

```python
pipeline = IngestPipeline()
bundle = pipeline.build_bundle(
    case_id="2026-042",
    bank_connector=FileBankRegulatorConnector(Path("banks.jsonl")),
    licensed_path=Path("vasp.jsonl"),
    control_path=Path("controls.jsonl"),
    kyt_path=Path("kyt_snapshot.jsonl"),
)
result = await pipeline.engine.fuse(bundle)
# result.attributions → FusedAttribution с bank_feed_ids, linkage_strength, evidence_chain
```

## Деплой для регулятора

- **On-prem / air-gap**: bulk KYT + JSONL банки
- **Neo4j**: все узлы и рёбра из EvidenceGraph
- **Аудит**: каждый вывод = `evidence_chain[]`
- **Персональные данные**: только `subject_id`, не ФИО в OSINT слое

## API (flowsint-api)

Префикс: `/api/compliance` (требуется auth token)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/cases` | Создать кейс `{ case_ref, investigation_id? }` |
| GET | `/cases/{id}` | Статус и результат fusion |
| POST | `/cases/{id}/bank-feeds` | Ingest batch банков (JSON, schema `regulator-hub/v1`) |
| POST | `/cases/{id}/fuse` | Запуск OSINT fusion |
| POST | `/kyt/import` | Upload `.jsonl` мировой KYT базы → PostgreSQL |

### Пример bank-feed batch

```json
{
  "schema_version": "regulator-hub/v1",
  "hub_id": "fiu-hub-ru",
  "exported_at": "2026-06-30T10:00:00Z",
  "feeds": [
    {
      "feed_id": "str-2026-001",
      "bank_name": "Sber",
      "bank_bic": "SABRRUMM",
      "alert_type": "crypto_suspicion",
      "region": "RU",
      "currency": "RUB",
      "amount": 250000,
      "subject_id": "subj-hash-abc",
      "linked_crypto_address": "TWallet...",
      "linked_chain": "tron",
      "reported_at": "2026-06-30T09:15:00Z"
    }
  ]
}
```

JSON Schema: `schemas/regulator_hub_v1_bank_feed.schema.json`

## Interop (Phase 4): followthemoney + GraphSense TagPack

FinSkalp exports and imports labels in the **followthemoney** ecosystem (same ndjson shape as OpenSanctions `entities.ftm.json`). Fusion investigation graphs export as FTM `entities` + `Payment` statements.

**GraphSense:** full server deployment is **deferred** (infra, AGPL, sovereign data policy). Instead:

- **TagPack CSV** (`address,currency,label`) → `entity_labels` via `interop/graphsense_tagpack.py`
- **Path-finding** on the local fusion `address_view` graph → `interop/graphsense_paths.py`

See `interop/GRAPHSENSE_STRATEGY.md` for rationale and operator steps.

**Marble (DFR Lab):** architecture study only — see [`docs/MARBLE_STUDY.md`](docs/MARBLE_STUDY.md) (no code import; case-workflow patterns borrowed in Phase 5).

### PostgreSQL

Таблицы (миграция `e7f8a9b0c1d2`):
- `compliance_cases` — кейсы регулятора
- `compliance_bank_feeds` — банковские feeds
- `compliance_kyt_labels` — мировая KYT база (upsert по chain+address)

## Roadmap

1. RegulatorAPIConnector — реальный HTTP/gRPC к хабу
2. PostgreSQL для LabelCache (миллиарды адресов)
3. P2P monitoring ingest
4. Case report PDF/JSON
5. Watchlist по hub-кластерам с высоким black_zone score
