# Graph Engine UX

## Principle

The graph is not a tab — it is the **persistent mission canvas**. In investigation mode, `FusionGraphStage` mounts once and survives panel toggles, dock tab switches, and MIO interactions.

## Wrapper Stack

```
FusionGraphStage
  └─ fusion-graph-hud (entity count, hop depth, confidence, LIVE)
  └─ ComplianceGraphView (ReactFlow + dagre)
       ├─ node pulse (SSE graphAlerts)
       ├─ risk propagation cascade (edge highlight)
       └─ temporal replay bar (non-compact mode)
```

## HUD Fields

| Field | Source |
|-------|--------|
| ENTITIES | `graph.nodes.length` |
| HOP DEPTH | BFS max depth from source nodes |
| CONFIDENCE | Mean node confidence × 100 |
| LIVE | SSE connection active (green dot) |

## Pulse Behavior

On `graphAlerts` from `useComplianceEvents`:

1. Target node receives `compliance-graph-node--alert` class
2. 1.6s box-shadow pulse (red operational)
3. Auto-clear after 8s if no repeat alert

## Risk Propagation

When alert fires:

1. Identify node by `payload.address` or `entity_key`
2. BFS outward to depth 2
3. Edges on path receive staggered `traced` flag (200ms per hop)
4. Non-path nodes dim to 0.35 opacity during cascade
5. Restore after 3s

## Replay

Temporal slider remains in graph footer (non-compact). Fusion uses `compact={false}` always in investigation.

## Pin Semantics

Double-click node toggles pin (existing). Pinned nodes listed in HUD corner.

## Performance

- `memo` on edge renderer (existing)
- HUD updates throttled 500ms
- Pulse animations GPU-only (box-shadow, opacity)
