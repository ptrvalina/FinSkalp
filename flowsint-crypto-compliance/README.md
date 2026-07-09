# FinSkalp · Crypto Compliance

Подсистема **FinSkalp** для **госрегулятора**: сужение серой зоны на стыке **фиат ↔ крипта**.

## Задача

Когда крипта проходит через лицензированную площадку, но дальше уходит на **немаркированные адреса**, регулятору нужно:

1. **Склеить** fiat-leg (FIU/банк) с on-chain путём
2. **Кластеризовать** серые адреса по локальным признакам (регион, OTC, лицензированные контрагенты)
3. **Оценить региональный профиль** (СНГ → Карибы, Индия → CEX-кластер и т.д.)
4. Выдать **вероятностный отчёт** с цепочкой доказательств, а не бинарную метку «это Bybit»

## Суверенная модель для РФ и СНГ (без международного KYT)

Международные провайдеры (Chainalysis, Elliptic, TRM) **напрямую с Россией не работают**.
Классические западные инструменты **не закрывают** серую и чёрную зону в СНГ.

### Чем заменяем KYT

| Слой | Источник | Что даёт |
|------|----------|----------|
| **Белый** | Лицензированные VASP РФ/СНГ, 115-ФЗ банки | Якоря: кто, когда, куда |
| **Серый** | Кластеризация + региональный профиль + коридоры | «Похоже на OTC RU», «транзит KZ→TR» |
| **Чёрный** | Поведенческие эвристики (hub, peel, layering) | Без внешней базы миксеров |

### Модули суверенного покрытия

- `cis/coverage.py` — юрисдикции СНГ, коридоры (RU→KZ→TR→AE), каналы on-ramp
- `heuristics/black_zone.py` — hub/layering без Chainalysis
- `engine/corridor_analyzer.py` — сопоставление с типовыми трансграничными маршрутами
- `engine/sovereign_attributor.py` — итоговая атрибуция только из domestic evidence

### Приоритет сетей для СНГ

1. **TRON (USDT)** — основной трансграничный коридор
2. **BTC** — крупные переводы, OTC
3. **ETH** — DeFi/мосты

### Источники данных (без иностранного KYT)

| Источник | Роль |
|----------|------|
| FIU / банковские алерты (115-ФЗ) | Fiat-leg, регион происхождения |
| Лицензированные площадки РФ/СНГ | Белые якоря |
| Контрольные закупки (P2P, OTC) | Заземление серых адресов |
| Мониторинг P2P-объявлений | Локальные on-ramp метки |
| Публичный блокчейн | Топология, hubs, peel chains |
| Обмен с регуляторами СНГ (KZ, BY) | Bilateral anchors |

## Источники данных (MVP)

| Источник | Роль |
|----------|------|
| FIU / банковские алерты | Fiat-leg, регион происхождения |
| Лицензированные площадки | Белые якоря: депозиты/выводы, jurisdiction |
| Контрольные закупки | Заземление серых адресов в реальный канал |

## Архитектура

```
┌─────────────────┐   ┌──────────────────┐   ┌─────────────────┐
│ FIU / Bank      │   │ Licensed Platform│   │ Control Purchase│
│ FiatLegEvent    │   │ LicensedPlatform │   │ ControlPurchase │
└────────┬────────┘   └────────┬─────────┘   └────────┬────────┘
         │                     │                      │
         └─────────────────────┼──────────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │     BridgeLinker     │
                    │  ClusterEngine       │
                    │  RegionProfiler      │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │ FiatCryptoBridge     │
                    │ CryptoCluster        │
                    │  → Neo4j graph       │
                    └──────────────────────┘
```

## Модули

- `flowsint-types/fiat_crypto.py` — типы графа: `FiatLegEvent`, `LicensedPlatformEvent`, `ControlPurchaseEvent`, `CryptoCluster`, `FiatCryptoBridge`
- `flowsint-crypto-compliance` — движок склейки и адаптеры BTC/ETH/TRON
- `flowsint-enrichers/crypto/compliance/` — enrichers для UI Flowsint

## OSINT-ядро (fusion)

Центральный оркестратор: **`OSINTFusionEngine`**

```
Банки (через регулятора) + VASP + Control Purchase + KYT bulk
        → EvidenceGraph → MergeEngine → FusedAttribution
```

Подробная архитектура: [ARCHITECTURE.md](./ARCHITECTURE.md)

### Interop: followthemoney & GraphSense TagPack

Phase 4 closes ecosystem compatibility without deploying full GraphSense:

| Format | Module | API |
|--------|--------|-----|
| EntityLabel ↔ FTM ndjson | `interop/ftm_adapter.py` | `GET/POST /api/interop/ftm/entity-labels` |
| Fusion graph FTM bundle | `interop/fusion_ftm_export.py` | `GET /api/interop/ftm/fusion-graph/{id}` |
| GraphSense TagPack CSV | `interop/graphsense_tagpack.py` | `POST /api/interop/graphsense/tagpack/import` |
| Local path-finding | `interop/graphsense_paths.py` | `GET /api/interop/graphsense/paths?from=…&to=…` |

Decision record: `src/flowsint_crypto_compliance/interop/GRAPHSENSE_STRATEGY.md`. Schemas: `schemas/entity_label_ftm_v1.schema.json`, `schemas/fusion_graph_ftm_export_v1.schema.json`.

### Ключевые модули

| Модуль | Роль |
|--------|------|
| `osint_core/fusion_engine.py` | Главный оркестратор |
| `osint_core/evidence_graph.py` | Граф доказательств |
| `osint_core/entity_resolver.py` | Склейка bank→subject→wallet |
| `osint_core/link_scorer.py` | Сила связи bank↔crypto |
| `osint_core/merge_engine.py` | Sovereign + international merge |
| `ingestion/bank_regulator.py` | Коннектор банков через регулятора |
| `ingestion/international_kyt.py` | Bulk мировых баз |
| `ingestion/pipeline.py` | Сборка кейса |

### Enrichers

| Имя | Вход | Выход |
|-----|------|-------|
| `wallet_to_fused_attribution` | CryptoWallet | **FusedAttribution** (полный fusion) |
| `fiat_alert_to_crypto_bridge` | FiatLegEvent | FiatCryptoBridge |
| `wallet_to_cluster_profile` | CryptoWallet | CryptoCluster |

## Пример сценария (СНГ → Доминикана)

1. FIU-алерт: рублёвый перевод, регион `RU`
2. Контрольная закупка P2P: `TGray1 → TGray2`
3. On-chain: `TGray2 → TDOExchange`
4. Лицензированная CEX в DO принимает на `TDOExchange`

Результат: `FiatCryptoBridge` с `region_origin=RU`, `region_destination=DO`, confidence и evidence chain.

## Демо для госрегулятора

**Боевой прототип** — см. [DEMO_REGULATOR.md](./DEMO_REGULATOR.md)

## Веб-стенд (для презентации в реальном времени)

```bash
cd flowsint
uv sync
uv run flowsint-regulator-stand
```

Откройте в браузере:

| Адрес | Когда использовать |
|-------|-------------------|
| **http://localhost:8877** | С вашего ноутбука |
| **http://\<ваш-IP\>:8765** | Показ на проекторе / планшете регулятора в той же сети |

Windows: двойной клик `scripts/start_demo_stand.bat`

На странице — 4 сценария, кнопка **«Запустить анализ»** → результат за 1–2 сек (OSINT fusion в реальном времени).

## CLI (терминал)

```bash
uv run flowsint-regulator-demo --scenario all
```

## Запуск тестов

```bash
cd flowsint-crypto-compliance
uv run pytest tests/
```

## Blockscout (ETH / BSC / Polygon)

Live EVM collectors use Blockscout's Etherscan-compatible API (`chains/blockscout_client.py`):

| Env | Default |
|-----|---------|
| `FINSKALP_BLOCKSCOUT_ETH_URL` | `https://eth.blockscout.com/api` |
| `FINSKALP_BLOCKSCOUT_BSC_URL` | `https://bsc.blockscout.com/api` |
| `FINSKALP_BLOCKSCOUT_POLYGON_URL` | `https://polygon.blockscout.com/api` |

Self-hosted Blockscout: see `docker/docker-compose.blockscout.yml` (stub) and [Blockscout deployment docs](https://docs.blockscout.com/setup/deployment/docker-compose-deployment). Polygon watchlist entries: `polygon:0x…` in `FINSKALP_KYT_WATCHLIST`.

## Дальнейшие шаги

- [ ] API загрузки фидов FIU / 115-ФЗ и лицензированных площадок
- [ ] Мониторинг P2P-объявлений (локальные площадки) → ControlPurchaseEvent
- [ ] Bilateral exchange с регуляторами KZ, BY, AM
- [ ] Связка enricher ↔ все сиды расследования в одном sketch
- [ ] Case report (PDF/JSON) для следственного контура
- [ ] ~~KYT-провайдеры~~ — не используем как ground truth для РФ/СНГ

## Production ops (Direction 3–4)

- **API:** case workflow, batch screening, bank webhooks, watchlist, FZ115 XML — see [RUNBOOK.md](./RUNBOOK.md)
- **Load:** `k6 run k6/batch-screening.js`
- **E2E:** `npx playwright test -c playwright.config.ts`

## Правовая рамка

Система даёт **вероятностную аналитику для расследований**, не является доказательством владения адресом. Все персональные данные — псевдонимизированные (`subject_id`, `user_ref`).
