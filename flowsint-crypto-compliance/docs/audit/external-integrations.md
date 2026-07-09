# Внешние интеграции

**RFC-0001 · Глава 12** · Статус: Draft · Дата: 2026-07-08

## Критичность

| Tier | Описание |
|------|----------|
| **P0 Critical** | Без сервиса prod не работает |
| **P1 Major** | Сильная деградация, есть fallback |
| **P2 Optional** | Feature-level |

---

## FinSkalp-native

| Интеграция | Tier | Entry point | Fallback |
|------------|------|-------------|----------|
| PostgreSQL | P0 | `flowsint_core.core.postgre_db` | Demo in-memory |
| Redis / Celery | P1 | `celery.py`, `live_cache.py` | Sync inline |
| TronGrid | P0 (TRON) | `chains/on_chain_provider.py` | Sovereign node |
| Sovereign TRON | P2 | `docker-compose.tron-fullnode.yml` | TronGrid |
| OpenSanctions | P1 | `live_collectors.py` | Offline bootstrap |
| OFAC SDN | P1 | `attribution/open_datasets.py` | Local JSON |
| Etherscan / Blockscout | P2 | `chains/eth.py`, `blockscout_client.py` | Chain skip |
| BscScan / Polygonscan | P2 | `live_collectors.py` | Blockscout |
| mempool.space / Blockstream | P2 | BTC collectors | — |
| Solana RPC | P2 | `chains/solana.py` | — |
| Ahmia (clearnet/Tor) | P2 | `darknet_tor.py`, `live_collectors` | Local corpus |
| BitcoinAbuse | P2 | `live_collectors` | Local corpus |
| Maigret / SpiderFoot | P2 | Scalpel collectors | Skip if missing |
| Wayback Machine | P2 | `osint/evidence_preservation.py` | HTML hash only |
| Meilisearch | P2 | `search/meilisearch_client.py` | Postgres ILIKE |
| Unleash | P2 | `infrastructure/feature_flags.py` | Env flags |
| OTLP / Tempo | P2 | `observability/tracing.py` | No tracing |
| Neo4j | P1 | `graph_store.py` | Memory backend |
| Playwright | P2 | `evidence_preservation.py` | No screenshot |

---

## Flowsint enrichers (adjacent)

Sherlock, Holehe, HIBP, Hudson Rock, DeHashed, crt.sh, ip-api, Whois — через `flowsint-enrichers`, не FinSkalp core path.

---

## Зависимость от внешнего API = риск

Если **TronGrid + sovereign TRON** недоступны одновременно — TRON-расследования блокируются (до 300s timeout, `COMPLIANCE_INVESTIGATE_TIMEOUT_SEC`).

**Рекомендация Volume II:** circuit breaker dashboard + SLA per provider (уже частично в `circuit_breaker.py`).

---

## Self-hosted альтернативы (RFC-0000 Principle 10)

| SaaS-аналог | Self-hosted в репо |
|-------------|-------------------|
| Datadog traces | Tempo + Grafana (`docker-compose.hardening.yml`) |
| Algolia | Meilisearch |
| LaunchDarkly | Unleash |
| TronGrid only | java-tron fullnode compose |
