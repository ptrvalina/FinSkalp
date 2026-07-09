# Changelog

All notable changes to FinSkalp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — FinSkalp (phases 1–5 + backlog)

- **FinSkalp crypto compliance platform** (`flowsint-crypto-compliance`) — sovereign RF/CIS regulatory OSINT, multihop fusion, forensic reporting (115-ФЗ), demo ops center on `:8877`, and `flowsint-app` compliance kanban.
- **Phase 1 — Integrity:** live TronGrid E2E, volumetric attribution fix, priority lead, honest Scalpel checkboxes, Postgres `entity_labels` in combat mode.
- **Phase 2 — Sovereign infra:** java-tron FullNode Docker stack, `OnChainProvider` failover, sovereign badges in reports.
- **Phase 3 — Graph UX:** cluster drill-down, exposure paths, Arkham-style side panel, timeline/pins/saved views, risk token system, JSON/GraphML/PNG export.
- **Phase 4 — Interop:** followthemoney ndjson import/export, GraphSense TagPack CSV, local path-finding API.
- **Phase 5 — Second tier:** Blockscout/Polygon collector, co-spend methodology doc, DeFi detector, case workflow UI, security audit fixes, Marble architecture study.
- **Premium UI:** FinSkalp design tokens, graph workspace layering, ops center hero metrics.
- **Backlog:** sigma.js WebGL renderer (>200 nodes), Solana RPC collector, server-side graph views API, Blockscout self-host compose, GraphSense ADR-004 (deferred), sovereign TRON setup scripts, dedicated CI workflow (`finskalp-compliance.yml`).

### Changed

- Graph saved views migrate from `localStorage` to `GET/POST/DELETE /api/investigations/{id}/graph/views` with offline fallback.
- `GET /api/infra/tron-node` documents snapshot sync state and health gate.
