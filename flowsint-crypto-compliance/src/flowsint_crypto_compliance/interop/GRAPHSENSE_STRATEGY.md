# GraphSense integration strategy — FinSkalp

## ADR-004: Defer full GraphSense server deployment

| Status | **Deferred** (accepted 2026-07-03) |
|--------|-------------------------------------|
| Decision makers | FinSkalp platform / compliance engineering |
| Revisit trigger | Regulator requires BTC UTXO-scale path API on indexed full-chain graph |

### Context

GraphSense provides Elasticsearch + Spark + REST path analytics on full-chain indexes. FinSkalp Phase 4 needed **label interoperability** and **path-style exports**, not a second graph database.

### Decision

**Chosen:** lightweight **TagPack CSV** import + **local path-finding** on FinSkalp fusion graphs.

**Deferred:** full GraphSense server deployment (Docker stack, Elasticsearch, Spark, REST API).

### Consequences

- **Positive:** zero extra infra on demo stand; sovereign data stays in FinSkalp Postgres/`entity_labels`; AGPL runtime avoided.
- **Negative:** no native GraphSense REST for billion-edge BTC graphs; path depth limited to fusion `address_view` hop budget.
- **Migration path if deferred is reversed:** see [Full deploy checklist](#full-deploy-checklist) below.

---

## Rationale (summary)

| Factor | TagPack + local paths | Full GraphSense deploy |
|--------|----------------------|------------------------|
| Infra | CSV file or URL; no extra services | Java/Spark/ES cluster; ops-heavy |
| License | Public TagPack format; no AGPL runtime | GraphSense core is AGPL — sovereign deploy review |
| Data policy | Labels stay in FinSkalp `entity_labels`; no third-party graph upload | Requires syncing chain data to GS backend |
| Demo stand | Works offline with bundled seed + fusion graph | Multi-day setup; not suitable for regulator laptop demo |
| Path analysis | Reuses fusion `address_view` edges + BFS/DFS | Native GS path API needs indexed full-chain graph |

Full GraphSense remains valuable for **BTC UTXO-scale** analytics; FinSkalp already covers TRON/ETH screening via TronGrid and sovereign node options (Phase 2). Phase 4 closes interoperability via **followthemoney** export/import and **TagPack-compatible** labels.

## TagPack format

CSV header (GraphSense community TagPack convention):

```csv
address,currency,label,category,confidence,risk_score
```

- `currency`: `trx`, `eth`, `btc` (mapped to FinSkalp chains)
- Optional `chain` column overrides currency mapping
- Bundled file: `data/attribution/graphsense_tagpack.csv`
- Remote: set `FINSKALP_GRAPHSENSE_TAGPACK_URL` to a public TagPack CSV

## Bootstrap order

1. `graphsense_seed.csv` (legacy bundled seed)
2. `graphsense_tagpack.csv` (TagPack format)
3. Optional URL tagpack (`FINSKALP_GRAPHSENSE_TAGPACK_URL`)

Loaded in `bootstrap_open_datasets()` as source `graphsense_tagpack`.

## Path-finding

`interop/graphsense_paths.py` runs on **investigation fusion graphs** (`address_view` nodes/edges), not the GraphSense API:

- `GET /api/interop/graphsense/paths?from=…&to=…&investigation_id=…`
- Returns GraphSense-style `{ paths: [{ length, node_ids, nodes }] }`

For exposure-to-sanction paths from root, see `reporting/graph_top_tier.py` → `exposure_paths`.

## Adding new TagPack files

1. Export or obtain a public TagPack CSV (no proprietary leaked DBs).
2. Place at `data/attribution/graphsense_tagpack.csv` or set `FINSKALP_GRAPHSENSE_TAGPACK_URL`.
3. Restart demo server (bootstrap runs once) or `POST /api/interop/graphsense/tagpack/import` with CSV body.
4. Verify: `GET /api/interop/ftm/entity-labels?chain=tron` includes `source=graphsense` rows.

## FTM interop

Entity labels export as OpenSanctions-compatible ndjson (`schema: CryptoWallet`). Fusion graphs export as FTM `entities` + `Payment` statements. Schemas: `schemas/entity_label_ftm_v1.schema.json`, `schemas/fusion_graph_ftm_export_v1.schema.json`.

## Full deploy checklist (out of scope today)

If a jurisdiction mandates GraphSense-native path API on full BTC graph:

1. **Legal** — AGPL review for on-prem sovereign distribution; data-processing agreements for chain replica.
2. **Infra** — GraphSense Docker stack (Spark, ES, REST), ≥N TB disk for BTC index, dedicated ops runbook.
3. **Data** — Import chain blocks into GraphSense backend; schedule delta sync.
4. **Interop** — Replace `graphsense_paths.py` local BFS with GraphSense REST client; keep TagPack → `entity_labels` as primary label plane.
5. **FinSkalp** — Feature flag `FINSKALP_GRAPHSENSE_API_URL`; dual-write labels during migration window.
6. **Validation** — Golden-path tests: sanction exposure paths vs. local fusion graph on sample investigations.

Until then, operators use TagPack CSV + `GET /api/interop/graphsense/paths` on fusion graphs (Phase 4 closed).
