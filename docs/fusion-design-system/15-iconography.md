# Iconography

## Library

Lucide React — consistent with codebase. Fusion overrides:

```css
.fusion-rail .lucide { width: 16px; height: 16px; stroke-width: 1.5; opacity: 0.9; }
```

## Rail Icons

| Section | Icon | Meaning |
|---------|------|---------|
| COMMAND | `Radar` | National command center |
| INVESTIGATE | `Crosshair` | Active investigation |
| INTELLIGENCE | `Radio` | Live feed |
| GRAPH | `GitBranch` | Graph-first layout |
| QUEUE | `ListOrdered` | Case queue |
| LEGACY | `Archive` | Pre-fusion routes |

## Semantic Icons (inline only)

| State | Icon |
|-------|------|
| Pinned | `Pin` |
| Live SSE | `Circle` filled green |
| SLA breach | `Clock` + red |
| Critical alert | `AlertTriangle` |
| Evidence | `FileSearch` |
| Wallet | `Wallet` |

## Prohibited

- Emoji in UI
- Custom illustration sets
- Colored icon backgrounds
- Icon-only buttons without `aria-label`

## Entity Icons (graph)

Defer to existing node `kind` text labels in Phase 0. Phase 2: mono glyphs per entity type from `getKnowledgeModel`.

## Size Scale

| Context | px |
|---------|-----|
| Rail | 16 |
| Panel chrome | 12 |
| Inline table | 11 |
| HUD | 10 |
