# Отчёт по производительности

**RFC-0001 · Глава 15** · Статус: Draft · Дата: 2026-07-08

---

## Узкие места

| Операция | Механизм | Конфиг / файл | Severity |
|----------|----------|---------------|----------|
| **FinSkalp investigate** | Full pipeline: screening → Scalpel → fusion → attribution → PDF | `COMPLIANCE_INVESTIGATE_TIMEOUT_SEC=300` | **S** |
| **Multi-hop fusion** | BFS до 3 hops, on-chain + sanctions per hop | `FINSKALP_MAX_HOPS`, `FINSKALP_FUSION_TX_LIMIT=80` | **S** |
| **TRC20 fetch** | До 300 transfers на адрес | `live_collectors.py:262` | **M** |
| **Scalpel sequential waves** | Collectors inline или Celery | `scalpel/engine.py` | **M** |
| **PDF (WeasyPrint)** | Sync render | `reporting/pdf_report.py` | **M** |
| **Postgres label bootstrap** | Full table scan при init | `postgres_entity_store.py` | **M** |
| **Neo4j export** | Per-node Cypher, no batch | `neo4j_exporter.py` | **M** |
| **Collector health (full)** | Live ping всех collectors | До 45s — **только** `/api/osint/collector-health` | **L** (fixed for `/api/health`) |
| **Fusion distributed lock** | 180s TTL, parallel → empty graph | `multihop_fusion.py` | **M** |

---

## Уже внедрённые оптимизации

| Паттерн | Файл |
|---------|------|
| Circuit breakers per source | `infrastructure/circuit_breaker.py` |
| Redis live cache + TTL | `osint_core/live_cache.py` |
| Hot indexes (pgHero targets) | `l4m5n6o7p8q9_compliance_hot_indexes.py` |
| CQRS read snapshots | `ComplianceReadSnapshot` |
| Non-blocking health | `collector_health.py` background daemon |
| Idempotency + Redis lock | `idempotency.py`, `distributed_lock.py` |
| Priority queue OSINT | `osint/priority_queue.py` |

---

## Горизонтальное масштабирование

| Компонент | Масштабируется? | Ограничение |
|-----------|-----------------|-------------|
| flowsint-api | Да (stateless) | DB, Neo4j |
| Celery workers | Да | Queue depth, rate limits external APIs |
| regulator-stand | Нет (monolith + in-memory inbox) | Single process |
| Multi-hop fusion | Частично | Lock per address |
| live_cache memory fallback | Нет | Not shared across workers |

---

## Рекомендации Volume II

1. Async PDF generation (Celery task + poll)
2. Batch Neo4j UNWIND writes
3. Pagination / cursor для entity_labels bootstrap
4. Investigate phase spans → Grafana SLO dashboard (tracing уже есть)
