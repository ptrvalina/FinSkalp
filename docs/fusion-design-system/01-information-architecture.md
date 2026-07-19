# Information Architecture — Fusion

## Operator Personas

| Persona | Primary surface | Goal |
|---------|-----------------|------|
| Duty Officer | Command Center | Triage queue, SLA posture, national threat picture |
| STR Analyst | Investigation Workspace | Evidence fusion, graph traversal, hypothesis testing |
| Senior Reviewer | Investigation + MIO | Confidence validation, filing recommendation |
| Platform Engineer | Legacy tools routes | Enrichers, flows — unchanged |

## Site Map (Fusion Layer)

```
/dashboard/fusion                          Command Center (4 zones)
/dashboard/fusion/investigation/:caseRef   Investigation Workspace
/dashboard/compliance                      LEGACY — preserved
/dashboard/                                LEGACY dashboard
```

## Entity Model (UI-facing)

| Entity | Source | Display |
|--------|--------|---------|
| Case | `listCases`, `listInbox` | `case_ref`, workflow_status, priority |
| Evidence Graph | `getGraph` | Nodes (entity), edges (relation + strength) |
| Timeline Event | `getCaseTimeline` | Chronological mission log |
| Live Event | `useComplianceEvents` | Ticker + graph pulse |
| Wallet Screen | `screenWallet` | Risk score, confidence dimensions |
| Workflow | `getWorkflowStats` | Pipeline counts |

## L0–L4 Hierarchy

```
L0  Mission Strip     14-field operational posture — always visible
L1  Graph Stage       Center canvas — never unmounts in investigation
L2  Zone Panels       Timeline, evidence, hypotheses, queue
L3  Dock              Transactions, OSINT, documents, reports
L4  Progressive       Hover traces, expandable rows, pin nodes
```

## Navigation Model

**FusionRail** replaces SaaS sidebar within fusion routes:

- COMMAND — national overview
- INVESTIGATE — active case queue
- INTELLIGENCE — live feed focus
- GRAPH — graph-first layout preset
- QUEUE — case queue focus
- LEGACY — link-out to preserved routes

Rail is icon-only (48px), section labels on hover — not a CRUD menu.

## Data Truth Rules

- Missing API fields render `—` (em dash), never fabricated
- Confidence shown to one decimal when numeric
- Timestamps: `ru-RU` locale, 24h operational format
- Risk levels map to operational color tokens only

## Cross-Case Intelligence

`getCrossCaseGraphLinks` surfaces in graph HUD when case context active. Links appear as secondary edge highlights, not separate views.
