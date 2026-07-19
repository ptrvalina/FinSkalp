# UX Architecture — Fusion

## Cognitive Model

Analysts operate a **mission**, not a form. Every screen answers:

1. What is happening?
2. Why does it matter?
3. What is most urgent?
4. What is the next action?

## Screen Taxonomy

| Screen | Layout engine | Graph role |
|--------|---------------|------------|
| Command Center | 4-zone grid | Preview / national context |
| Investigation | 3-column + bottom dock | **Persistent center stage** |
| Legacy compliance | Tab shell | On-demand (deprecated path) |

## Interaction Primitives

| Primitive | Behavior |
|-----------|----------|
| Slide panel | Enters from edge, pushes layout |
| Dock panel | Resizable split, pinned to zone |
| Float panel | Detached hint; Phase 3 multi-monitor |
| Pin | Node or panel locked to layout |
| Trace | Edge hover highlights propagation path |
| Pulse | SSE alert animates target node |

## State Persistence

| Key | Scope |
|-----|-------|
| `fusion-layout-command` | Command center zone sizes |
| `fusion-layout-investigation` | Investigation panel splits |
| `fusion-panel-pins` | Pinned panel IDs |
| `finskalp-graph-pinned-{caseRef}` | Graph node pins (existing) |

## Error & Empty States

- Empty graph: centered monospace `NO GRAPH DATA — AWAITING FUSION`
- Loading: skeleton-free; opacity pulse on zone chrome only
- API failure: red operational strip cell, retry action card in MIO

## Accessibility

- Keyboard-first zone switching (see `19-keyboard-ux.md`)
- Focus rings: 1px `--fusion-ops-blue`
- Reduced motion: disable pulse/cascade, keep opacity transitions

## Anti-Patterns (Hard Reject)

- Centered hero cards with illustrations
- Floating action buttons
- Toast stacks covering graph
- Avatar circles in data tables
- Rounded-2xl card grids

## Reference Philosophy

| Product | Expensive because |
|---------|-------------------|
| Palantir Gotham | Object-centric; graph is home; every panel serves the canvas |
| Chainalysis Reactor | Transaction graph is live; risk propagates visually |
| IBM i2 | Analyst-built layouts; density without clutter |
| Bloomberg Terminal | Information strip + monospace discipline |
| NASA Mission Control | Status strips, zones, no decorative UI |

We adopt the **why**, not the visual copy.
