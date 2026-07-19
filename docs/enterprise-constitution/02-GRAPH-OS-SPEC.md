# Graph OS Specification

## Core Principle

The graph is not a visualization widget — it is the **primary operating surface**. Analysts pan, select, replay, and act on the graph the way operators use a terminal shell.

---

## Persistence Rules

| Rule | Implementation |
|------|----------------|
| No remount on resize | `FusionGraphStage` `persistent` prop on investigation |
| Preview on Mission Control | First queue case graph; compact HUD |
| Route continuity | Investigation → graph tab uses same data query key per `caseId` |
| Detached sync | `BroadcastChannel` `finskalp-fusion-{caseRef}` |

---

## Live Sync

- SSE via `useComplianceEvents` — alert overlays on graph
- Graph mutations invalidate `['fusion', 'graph', caseId]` only — not full page
- Risk propagation from `getCaseRiskHistory` → mission strip, not separate widget

---

## Layers (Z-Order)

1. Base entity nodes (wallet, person, org, exchange)
2. Transaction / flow edges
3. Evidence link highlights
4. Cross-case link overlay (`getCrossCaseGraphLinks`)
5. Alert / selection / hop-lens emphasis

---

## HUD Controls

| Control | Behavior |
|---------|----------|
| Cluster chip | Node/edge counts from payload |
| Hop lens | BFS ≤N hops from selected node |
| Temporal replay | Scrub index filters edges by time |
| Export | PNG/SVG snapshot |
| Detach | Opens `/graph` route |

---

## Performance Targets

| Metric | Phase 1 | Phase 6 |
|--------|---------|---------|
| Route paint → graph visible | <100ms skeleton | <50ms |
| Pan/zoom frame budget | 60fps @ 2k nodes | 60fps @ 1M nodes (GPU) |
| Live event overlay | <200ms from SSE | <100ms |

Phase 1 uses `ComplianceGraphView` (force/canvas). Million-node GPU engine is **explicitly deferred**.

---

## Stubs Allowed (Future Phases)

- Money flow particle engine — placeholder HUD chip OK
- Collaboration cursors — not in Phase 1
- Cinematic executive mode — not in Phase 1

---

## Constitution Violations

- Graph relegated to bottom-right quarter ← fixed in v3 Mission Control
- Graph inside a "card" with padding/shadow ← use full-bleed stage
- Full page reload on case switch within investigation ← use query invalidation only
