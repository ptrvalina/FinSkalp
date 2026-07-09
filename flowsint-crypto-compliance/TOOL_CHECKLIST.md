# FinSkalp Tool Health Checklist

Run: `python scripts/finskalp_health_check.py` from `flowsint-crypto-compliance`.

## Scalpel — чекбоксы «Центр OSINT» (UI ↔ backend)

| ID (чекбокс) | Название в UI | Статус | Примечание |
|--------------|---------------|--------|------------|
| `onchain_explorer` | ON-CHAIN EXPLORER | **works** | TronGrid live · `collect_tron_trc20_transfers` |
| `sanctions_watchlist` | САНКЦИИ | **works** | OFAC SDN + OpenSanctions API |
| `username_social` | USERNAME / MAIGRET | **works** | Maigret live · usernames из wave-0 entity_extractor |
| `abuse_scam_registry` | ABUSE / SCAM | **partial** | BitcoinAbuse (BTC) + локальный корпус |
| `darknet_index` | DARKNET INDEX 🔥 | **partial** | Ahmia clearnet + локальный darknet-корпус |
| `darknet_tor` | DARKNET · TOR 🧅 | **partial/works** | Ahmia clearnet live · Tor SOCKS авто 9050 или `FINSKALP_TOR_SOCKS` |
| `clearnet_intel` | CLEARNET ДОРК | **works** | Публичные dork-индексы |
| `vasp_registry` | РЕЕСТР VASP СНГ | **works** | `data/cis_vasp_registry.json` · 115-ФЗ |
| `court_enforcement` | СУД / ENFORCEMENT | **works** | DOJ/Europol seizure store |
| `reverse_whois_dns` | REVERSE WHOIS / DNS | **works** | RDAP/DNS · домены из URL/текста wave-0 |

Кнопки **«все» / «снять»** — только для `selectable` коллекторов (не трогают disabled Tor).

API: `GET /api/scalpel/collectors` возвращает `status`, `selectable`, `default_checked`, `tor_probe`.

## Backend / pipeline

| Инструмент | Статус | Примечание |
|------------|--------|------------|
| TronGrid balance + tokens | works | `TronChainAdapter.get_account_state` |
| Attribution Engine | works | Co-spend + open datasets + entity_labels |
| Multi-hop fusion graph | works | Label store на узлах · cluster_view |
| Graph UI side-panel | works | Entity-карточка · risk badge · sparkline · portfolio |
| Graph PDF (TronGrid-style SVG) | works | `svg_graph_style.py` |
| Forensic Report v2 | works | §8 flow + fusion graph |
| ETH live collector | works | `collect_eth_chain` · Etherscan v2 · `ETHERSCAN_API_KEY` |
| Polygon live collector | works | `collect_polygon_chain` · Blockscout · `FINSKALP_BLOCKSCOUT_POLYGON_URL` |
| Case workflow kanban | **works** | demo :8877 kanban + flowsint-app · API workflow stats |

## Топ-5 граф (промт 2026-07)

| ID | Функция | Статус |
|----|---------|--------|
| A1 | cluster_view + drill-down | **works** |
| A2 | direct/indirect exposure paths | **works** · кнопка Exposure в toolbar |
| A3 | cross-chain hops (bridge heuristic) | **works** · фиолетовые рёбра |
| A4 | timeline slider + Play | **works** |
| A5 | analyst pins + saved views | **works** · pins + API `/graph/views` + localStorage fallback |
| A6 | perf 500+ узлов | **works** · auto-cluster >150 · WebGL sigma.js >200 nodes + toolbar toggle |
| A7 | export JSON/GraphML/PNG | **works** |
| B1 | multichain (TRON/BTC/BSC/ETH/Polygon/Solana fusion) | **works** · Solana via public RPC |
| B2 | KYT watchlist real-time | **works** · SSE on new tx fingerprint + `/api/kyt/watchlist` |
| B3 | risk-score API | **works** · `/api/v1/score/{address}` <500ms path |
| B4 | DeFi router detection | **works** · `defi_detector.py` |
| B5 | public `/status` metrics | **works** · `live_ops_metrics` hero + table |


1. **Demo:** `TZASfRXk51No5XHPDE2eCcXpS8F8t1jgwL`
2. **Live TRON** с историей — attribution из seed/co-spend
3. **Чистый** адрес — low risk без ложных sanctions

## Критерий готовности (промт 2026-07)

- Все чекбоксы либо **works/partial** с честным tooltip, либо **disabled** (Tor)
- Расследование → граф без наложения панелей → клик по узлу → entity-карточка
- Категория/risk из attribution, не `unknown`/15 по умолчанию где есть метки
- Единая risk-шкала: `--fs-risk-*` в графе, отчётах, side-panel
