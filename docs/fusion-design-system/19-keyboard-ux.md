# Keyboard UX

## Global (Fusion routes)

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Command palette (legacy hook, Phase 2 fusion commands) |
| `Ctrl+1` | Focus graph stage |
| `Ctrl+2` | Focus left timeline |
| `Ctrl+3` | Focus MIO panel |
| `Ctrl+4` | Focus bottom dock |
| `Ctrl+Shift+Q` | Open case queue (command center Alpha) |
| `Escape` | Collapse active non-pinned panel |

## Navigation

| Shortcut | Action |
|----------|--------|
| `G` then `C` | Go command center |
| `G` then `I` | Go investigation (last case) |
| `J` / `K` | Next/prev queue row (when queue focused) |
| `Enter` | Open selected case |

## Graph

| Shortcut | Action |
|----------|--------|
| `F` | Fit view |
| `P` | Pin selected node |
| `R` | Reset trace highlight |
| `Space` | Play/pause temporal replay |

## Layout

| Shortcut | Action |
|----------|--------|
| `Shift+Alt+R` | Reset fusion layout to defaults |
| `Ctrl+Alt+]` | Pin active panel |

## Implementation Phase

Phase 0: document only + `Escape` collapse. Phase 2: wire all shortcuts in `FusionShell`.

## Focus Rings

Visible 1px `--fusion-ops-blue` — never suppressed for density.
