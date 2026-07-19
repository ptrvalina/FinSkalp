# Component System — Fusion

## Namespace

All components: `flowsint-app/src/fusion/`  
Prefix: `Fusion*`  
CSS class prefix: `fusion-`

## Core Shell

| Component | Role |
|-----------|------|
| `FusionShell` | Full-viewport root; rail + mission strip + outlet |
| `FusionRail` | 48px icon rail; mission sections |
| `FusionMissionStrip` | 14-field L0 strip |
| `FusionZone` | Operational zone container with label + tone |

## Panels

| Component | Role |
|-----------|------|
| `FusionPanel` | Chrome: title, pin, collapse, detach hint |
| `FusionDock` | Bottom/side resizable dock |
| `FusionDataGrid` | Virtualized-ready table shell |

## Intelligence

| Component | Role |
|-----------|------|
| `FusionLiveFeed` | SSE ticker with fade-in |
| `FusionMIO` | Mission Intelligence Officer action cards |
| `FusionGraphStage` | Persistent graph wrapper + HUD |

## Composition Rules

1. Shell owns layout persistence
2. Zones contain Panels; Panels contain content
3. GraphStage is sibling to zones, not child of Panel (prevents unmount)
4. MIO never renders message bubbles — only `ActionCard` rows

## ActionCard (MIO internal)

```
┌─[PRIORITY]─── TITLE ──────────────────────┐
│ Rationale (1 line, monospace secondary)   │
│ [EXECUTE] [DEFER] [DISMISS]               │
└───────────────────────────────────────────┘
```

## DataGrid Columns

- Header: 9px uppercase tracking 0.16em
- Row height: 28px (3× density)
- Sort indicator: mono chevron, no icons in cells unless semantic
- Group header: `--fusion-surface-raised` 1px bottom border

## Props Conventions

- `tone?: 'neutral' | 'ops' | 'clear' | 'caution' | 'critical'`
- `pinned?: boolean`
- `onPinToggle?: () => void`
- `density?: 'compact' | 'operational'` (default operational)

## Legacy Bridge

Fusion components import from `@/api/compliance-service` and `@/hooks/use-compliance-events` only. No new fetch layers.
