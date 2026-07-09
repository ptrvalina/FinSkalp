# Marble (DFR Lab) — Architecture Study for FinSkalp

**Status:** study/reference only · **no code import** · Phase 5.1 (2026-07-03)

## What Marble provides

[Marble](https://github.com/checkmarble/marble) (Checkmarble / DFR Lab) is an open-source **transaction monitoring** stack aimed at AML/fraud teams:

| Capability | Marble | FinSkalp equivalent |
|------------|--------|---------------------|
| Rule engine | YAML/SQL-like rules on streaming decisions | `illegal_flow.py`, `detection/`, XGBoost + heuristics |
| Case manager | Investigation cases with status, assignee, comments | `case_workflow.py`, `operations_center.py`, Postgres `compliance_cases` |
| Alert ingestion | Webhooks + batch from data warehouse | Bank hub webhooks, KYT watchlist, STR inbox |
| Workflow states | Open → investigating → closed | `new → triage → investigating → pending_filing → filed → archived` |
| Audit trail | Decision log per alert | `compliance_audit_log`, case comments |
| RBAC | Org roles on cases | `compliance_rbac.py` (analyst → admin) |

Marble is optimized for **fiat payment rails** (cards, wires) with a warehouse connector; FinSkalp is **on-chain-first** with sovereign RF/CIS registries — different primary data plane, similar **case lifecycle** patterns.

## License compatibility

- Marble core: **Apache 2.0** (compatible with proprietary FinSkalp distribution).
- FinSkalp model: **proprietary** product; Apache 2.0 allows study and optional future integration of *unmodified* components with attribution, but we do **not** import Marble code in Phase 5.
- **Explicitly avoided:** AGPL stacks (Jube, OpenCTI) — incompatible with closed-source SaaS/on-prem licensing.

## What FinSkalp already has vs. borrowable concepts

| Concept | FinSkalp today | Could borrow from Marble (design only) |
|---------|----------------|----------------------------------------|
| Rule triggers | Pattern rules + live KYT scan | Declarative rule packs versioned per jurisdiction |
| Case queue | Ops inbox + compliance API cases | Unified kanban with SLA timers (implemented Phase 5.5) |
| Decision explainability | Forensic report + evidence graph | Structured “decision payload” JSON per transition |
| Batch replay | Batch screening Celery job | Offline rule replay on historical txs (future) |

## Decision: no Marble code import

1. **Domain mismatch** — Marble expects warehouse tables; FinSkalp graph is chain-native (TronGrid, Blockscout, fusion).
2. **Operational weight** — full Marble deploy adds Postgres rules engine + Go services; FinSkalp demo stand must stay single-process friendly.
3. **License diligence** — Apache 2.0 is OK, but dependency tree and branding require legal review before any embed; not needed for current roadmap.
4. **Sovereignty** — regulator narrative depends on domestic data paths; Marble’s default connectors are EU fintech-oriented.

**Action:** use this document and Marble’s public docs/README as **reference** for case workflow UX and rule-engine ergonomics only. Revisit integration only after explicit license + product sign-off.
