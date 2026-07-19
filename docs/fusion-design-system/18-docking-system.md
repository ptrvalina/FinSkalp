# Docking System

## Implementation

`react-resizable-panels` via `FusionDock` wrapper with fusion-themed handles.

## Handle Style

```css
.fusion-dock-handle { width: 3px; background: var(--fusion-border); }
.fusion-dock-handle:hover { background: var(--fusion-ops-blue); }
.fusion-dock-handle[data-active] { background: var(--fusion-ops-blue); }
```

## Dock Positions

| Position | Investigation default |
|----------|----------------------|
| bottom | Evidence / wallets / reports |
| left | Timeline (main split, not dock) |
| right | MIO (main split) |

Bottom dock tabs are **content switches**, not route changes — graph stays mounted.

## autoSaveId Keys

- `fusion-inv-dock` — bottom dock height %
- `fusion-inv-main` — L|M|R horizontal split

## Snap Points

Panel sizes snap to 4% increments on release (library default).

## Keyboard Resize

`Ctrl+Alt+↑/↓` adjusts bottom dock ±4% (Phase 2).

## Collapse Dock

`Ctrl+Alt+_` collapses bottom dock to 8% (tab bar only).

## Integration with Graph

Graph panel has `minSize={40}` — dock cannot compress graph below 40% viewport.
