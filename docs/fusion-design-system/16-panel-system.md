# Panel System

## No Modals

Dialogs, alert modals, and sheet overlays are **banned** in fusion routes. Confirmations use inline MIO action cards or strip status change.

## Panel Chrome (`FusionPanel`)

```
┌─ TITLE ──────────────── [PIN][COLLAPSE][DETACH] ─┐
│                                                   │
│  content slot                                     │
│                                                   │
└───────────────────────────────────────────────────┘
```

Height header: 32px. Border bottom 1px `--fusion-border`.

## States

| State | Width | Behavior |
|-------|-------|----------|
| Open | configured % | Resizable via handle |
| Collapsed | 0px | Recall from rail |
| Pinned | same | Survives layout reset |
| Detached | Phase 3 | `detach hint` shows multi-monitor shortcut |

## Slide vs Dock

- **Slide**: panel enters over sibling (z-index 10), used for temporary expansion
- **Dock**: permanent split member in `PanelGroup`

## Float (Phase 3)

Position fixed panel with drag handle — `fusion-panel--float` class reserved.

## Persistence

```ts
fusion-panel-pins: string[]  // panel IDs
fusion-panel-collapsed: Record<string, boolean>
```

## Focus

Clicking panel header focuses zone; `Escape` collapses non-pinned active panel.

## Z-Index Stack

```
0  graph canvas
5  graph HUD
10 panel content
15 mission strip
20 rail
30 live feed overlay (command center only)
```
