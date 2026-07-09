# FinSkalp OSINT Quality — Runbook

Institutional-grade OSINT: Bayesian fusion, source reliability, institutional memory,
evidence preservation, visual evidence chain, operational reliability.

## Quick start

```bash
# Optional deps (sovereign / self-hosted)
uv sync --package flowsint-crypto-compliance --extra osint-quality
playwright install chromium   # screenshots

# DB migration (flowsint-api)
cd flowsint-api && alembic upgrade head

# Stand
flowsint-regulator-stand
```

## Block A — Technical

### A1 Bayesian fusion (`osint/fusion_confidence.py`)

- **What:** Multiplies error probabilities across independent `dependency_group` keys.
- **Verify:**
  ```bash
  pytest flowsint-crypto-compliance/tests/test_osint_quality.py::test_bayesian_fusion_independent_vs_dependent -q
  ```
- **API:** `GET /api/osint/fusion-explain/{investigation_id}` after `POST /api/finskalp/investigate`.

### A2 Source reliability (`osint/source_reliability.py`)

- **Table:** `osint_source_reliability` (migration `m5n6o7p8q9r0`).
- **Auto-update:** `GET /api/osint/source-reliability` runs `sync_from_attribution_eval`.
- **Analyst feedback:** `POST /api/osint/source-reliability/feedback` with `source_name`, `confirmed`.
- **Flag:** `sample_size < FINSKALP_OSINT_RELIABILITY_MIN_SAMPLE` (default 5) → `insufficient_data_ru`.

### A3 Institutional memory (`osint/institutional_memory.py`)

- **Table:** `osint_findings` (tenant-scoped via `tenant_id` = `FINSKALP_TENANT_ID`).
- **Closed cases:** `workflow_status IN ('filed', 'archived')`.
- **Flag:** `PRIOR_CASE_MATCH` in screening findings with `prior_case_ref`.
- **Verify:** Index entity in case A, close case, run investigate on case B with same domain/username.

### A4 Evidence preservation (`osint/evidence_preservation.py`)

- **Storage:** `FINSKALP_EVIDENCE_DIR` (default `data/osint_evidence`).
- **Artifacts:** `page.html`, `screenshot.png`, SHA-256, Wayback URL.
- **API:** `GET /api/osint/evidence/{case_ref}/{hash_prefix}`.
- **Reports:** `report_link_ru` — snapshot URL + hash + date (not bare URL).
- **Playwright:** optional; HTML-only fallback if not installed.

### A5 Multilingual (`osint/multilingual.py`)

- **Detection:** offline Cyrillic/Latin heuristic.
- **Translation:** `argostranslate` optional extra `osint-quality`.
- **CIS regex:** KZ/UA/BY/UZ phones, KG INN, AM TIN in `entity_extractor.py`.

### A6 Continuous OSINT (`osint/continuous_osint.py`)

- **Rescan:** `POST /api/osint/continuous/rescan` — KYT watchlist addresses.
- **Interval:** `FINSKALP_OSINT_RESCAN_HOURS` (default 24).
- **Alerts:** SSE event `osint_watchlist_finding` (same bus as `watchlist_tx`).

## Block B — Visual

- **JS:** `static/js/evidence-chain.js` — SVG chain, icons, PRIOR CASE MATCH styling.
- **Wired in:** `app.js` FinSkalp result + `index.html`.
- **Verify:** Run investigate → evidence chain mount + fusion % in OSINT section.

## Block C — Functional reliability

| Module | Endpoint / hook |
|--------|-----------------|
| Collector health | `GET /api/osint/collector-health` (live ping); `/api/health` uses cached snapshot only |
| Query expansion | Scalpel `context` via `query_expansion.py` |
| Priority queue | `GET /api/osint/priority-queue` |
| Junk filter | `FINSKALP_OSINT_EMBED_JUNK=1` + `embeddings` extra |

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `FINSKALP_TENANT_ID` | demo UUID | Tenant isolation |
| `FINSKALP_EVIDENCE_DIR` | `data/osint_evidence` | Snapshots |
| `FINSKALP_OSINT_RESCAN_HOURS` | `24` | Watchlist rescan |
| `FINSKALP_COLLECTOR_HEALTH_MIN` | `15` | Health cache TTL |
| `FINSKALP_OSINT_EMBED_JUNK` | off | Embedding junk filter |

## Blockers

1. **Playwright / Chromium** — required for screenshots; HTML+hash works without.
2. **PostgreSQL** — institutional memory + reliability persistence need `DATABASE_URL` + migration.
3. **Argos language packs** — must be installed offline for translation (not bundled).
4. **sentence-transformers** — large download; only when `FINSKALP_OSINT_EMBED_JUNK=1`.

## Acceptance checklist

- [ ] Fusion explain shows `composite_pct` and per-source `raw × reliability`
- [ ] Duplicate Ahmia hits in same `dependency_group` do not double-count
- [ ] PRIOR CASE MATCH appears for entity seen in archived case (same tenant)
- [ ] URL finding has `html_sha256` and `discovery_at` in `preserved_evidence`
- [ ] `/api/health` includes `osint_collectors` status
- [ ] Evidence chain SVG renders after investigate
