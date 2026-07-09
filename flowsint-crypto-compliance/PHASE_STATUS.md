# FinSkalp — Phase Status

Сводка по MASTER ROADMAP (`finskalp_master_roadmap.md`). Фаза 1 закрыта; Фаза 3 закрыта; Фаза 4 закрыта (2026-07-03).

Источники детальных промтов (вне репозитория / Downloads):

| Фаза | Детальный промт |
|------|-----------------|
| 1 | `finskalp_final_master_prompt.md` (Items 1–3), `finskalp_data_density_prompt.md` (Задача 1), `finskalp_tools_graph_design_prompt.md` (Задача 1) |
| 2 | `finskalp_sovereignty_infra_prompt.md` (Задача 1) |
| 3 | `finskalp_top5_graph_prompt.md` (Блок A), `finskalp_tools_graph_design_prompt.md` (Задачи 2–3) |
| 4 | `finskalp_final_consolidated_opensource_prompt.md` (Уровень 2) |
| 5 | `finskalp_top5_graph_prompt.md` (Блок B), `finskalp_case_workflow_ui_prompt.md`, `finskalp_security_audit_prompt.md` |

---

## Фаза 1 — Целостность (приоритет: максимальный)

**Критерий закрытия:** живая демонстрация на новом адресе без зависаний, пустых полей атрибуции и ложных включённых чекбоксов Scalpel.

| # | Задача | Статус | Примечание |
|---|--------|--------|------------|
| 1 | Live E2E с `TRONGRID_API_KEY` на 3 адресах | **done** | Прогон 2026-07-03: `pass: true`, все 3 адреса; demo ~426s screen |
| 2 | Фикс пустой «Суверенная атрибуция» в объёмном отчёте | **done** | `reporting/volumetric_report.py` → `_serialize_attribution` |
| 3 | Priority Lead live через TronGrid | **done** | `resolve_priority_lead_live` в `forensic_builder.py` |
| 4 | Честные чекбоксы Scalpel | **done** | `TOOL_CHECKLIST.md` |
| 5 | Postgres `entity_labels` в combat mode | **done** | `resolve_entity_store_mode()` + `apply_combat_env_defaults()` |

**Вердикт фазы 1:** **closed** (2026-07-03) — E2E pass на 3 адресах; остальные пункты закрыты. Замечания: demo-screen ~7 мин; bootstrap OpenSanctions пустой (не блокирует).

---

## Последний E2E (`finskalp_e2e_verify.py`) — 2026-07-03

| case | address | total_ms | screen_ms | fusion_ms | pdf_ms | inbound | outbound |
|------|---------|----------|-----------|-----------|--------|---------|----------|
| demo | TZASf…jgwL | 426147 | 175384 | 71018 | 4361 | 250 | 2 |
| new_labeled | TQn9Y…bLSE | 188132 | 69743 | 48476 | 170 | 113 | 187 |
| clean | T9yD1…xuWwb | 93174 | 11599 | 69841 | 135 | 262 | 38 |

`trongrid_key_loaded: true`, `hash_reproducible: true`, `pass: true`. Priority lead на demo: `data_source: live_trongrid`.

---

## Фаза 2 — Суверенная инфраструктура (java-tron)

| # | Задача | Статус |
|---|--------|--------|
| 1 | java-tron FullNode (Docker + snapshot) | **done** | `docker/docker-compose.tron-fullnode.yml`, `docker/tron-fullnode/README.md` |
| 2 | `OnChainProvider` + TronGrid / sovereign | **done** | `chains/on_chain_provider.py` |
| 3 | Failover TronGrid | **done** | `FailoverOnChainProvider`, `FINSKALP_TRON_PROVIDER=failover` |
| 4 | Маркировка «данные с суверенного узла» в отчётах | **done** | `on_chain_source` в screening + forensic HTML badge |

**Вердикт фазы 2:** **closed** (2026-07-03)

---

## Фаза 3 — Витрина: граф-кластеры + дизайн

| # | Задача | Статус | Примечание |
|---|--------|--------|------------|
| 1 | Кластерная визуализация графа | **done** | `cluster_view` default · dbl-click expand/collapse in-place · size ∝ member_count + volume_usd |
| 2 | Direct vs indirect exposure | **done** | edge width/color · hop labels · click indirect → full path highlight (consecutive edges) |
| 3 | Side-panel узла (Arkham-style) | **done** | portfolio · sparkline · large risk badge (`entity-card`) |
| 4 | Развести слои UI | **done** | `graph-workspace` z-index/isolation · status cards не перекрывают canvas |
| 5 | Единая risk-цветовая система | **done** | `--fs-risk-*` в графе, side-panel, PDF SVG (`svg_graph_style.py`) |
| 6 | Timeline, аннотации, экспорт | **done** | slider+Play · pin notes on canvas · saved views (localStorage) · PNG/GraphML/JSON |

**Вердикт фазы 3:** **closed** (2026-07-03) — A1–A7 в demo UI; A6 >500 узлов: Canvas2D tuning (WebGL требует sigma.js fallback, см. `graph-viz.js`).

---

## Фаза 4 — followthemoney + GraphSense

| # | Задача | Статус | Примечание |
|---|--------|--------|------------|
| 1 | Схема `entity_labels` ↔ followthemoney | **done** | `interop/ftm_adapter.py` · `schemas/entity_label_ftm_v1.schema.json` |
| 2 | GraphSense: TagPack + local paths (no full deploy) | **done** | `interop/graphsense_tagpack.py` · `GRAPHSENSE_STRATEGY.md` |
| 3 | FTM fusion export + interop API | **done** | `GET/POST /api/interop/ftm/*` · `GET /api/interop/graphsense/paths` |

**Вердикт фазы 4:** **closed** (2026-07-03) — FTM ndjson import/export; fusion graph FTM bundle; GraphSense TagPack CSV; path-finding on own fusion graph.

---

## Фаза 5 — Второй эшелон

| # | Задача | Статус | Примечание |
|---|--------|--------|------------|
| 1 | Marble (изучение) | **done** | `docs/MARBLE_STUDY.md` · no code import |
| 2 | Blockscout мультичейн | **done** | `chains/blockscout_client.py` · Polygon collector · registry + Celery |
| 3 | BlockSci co-spend методология | **done** | `docs/BLOCKSCI_COSPEND.md` · EVM contract+method clusters |
| 4 | Мультичейн, watchlist API, DeFi | **done** | Polygon B1 · watchlist tx SSE · `/status` · `/api/v1/score` |
| 5 | Case workflow UI | **done** | Demo kanban :8877 · flowsint-app kanban · RBAC viewer |
| 6 | Security-аудит | **done** | `SECURITY_AUDIT.md` · 3 High fixed · tests |

**Вердикт фазы 5:** **closed** (2026-07-03) — Blockscout/Polygon live; kanban on demo + app; security pass with fixes. Замечания: Polygon watchlist needs `polygon:0x…` prefix (0x collision with ETH); full Blockscout self-host optional via `docker/docker-compose.blockscout.yml`.

---

## Backlog (post phases 1–5) — 2026-07-03

| # | Item | Статус | Примечание |
|---|------|--------|------------|
| 1 | WebGL graph (sigma.js) 500+ nodes | **done** | `graph-viz.js` auto >200 · toolbar WebGL toggle · `prefers-reduced-motion` |
| 2 | Sovereign java-tron production readiness | **done** | `setup_sovereign_tron.{sh,ps1}` · snapshot gate in `/api/infra/tron-node` · `make sovereign-tron-up` |
| 3 | Solana + additional chains | **done** | `chains/solana.py` · `collect_solana_chain` · fusion/registry/UI · `test_solana_collector.py` |
| 4 | Server-side saved graph views | **done** | `ComplianceGraphView` + migration · `GET/POST/DELETE …/graph/views` · API + localStorage fallback |
| 5 | Blockscout self-hosted stack | **done** | `docker-compose.blockscout.yml` + `docker/blockscout/README.md` · `.env.example` |
| 6 | GraphSense full deploy decision | **done** | ADR-004 deferred in `GRAPHSENSE_STRATEGY.md` + migration checklist |
| 7 | Marble study | **done** | `docs/MARBLE_STUDY.md` · cross-link `ARCHITECTURE.md` |
| 8 | CI for flowsint-crypto-compliance | **done** | `.github/workflows/finskalp-compliance.yml` |
| 9 | CHANGELOG | **done** | Root `CHANGELOG.md` FinSkalp entry |
