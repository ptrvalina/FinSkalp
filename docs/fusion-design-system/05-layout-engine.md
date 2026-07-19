# Layout Engine

## Engine Choice

`react-resizable-panels` v3 — same primitive as legacy, new `autoSaveId` keys:

| Surface | autoSaveId |
|---------|------------|
| Command horizontal | `fusion-command-h` |
| Command vertical | `fusion-command-v` |
| Investigation main | `fusion-inv-main` |
| Investigation dock | `fusion-inv-dock` |

## Panel Zones

```
ZONE_ALPHA   top-left quadrant
ZONE_BRAVO   top-right quadrant  
ZONE_CHARLIE bottom-left
ZONE_DELTA   bottom-right
```

Investigation overrides to L-M-R + bottom dock (see `09-investigation-workspace.md`).

## Constraints

| Panel | minSize | maxSize | defaultSize |
|-------|---------|---------|-------------|
| Left context | 12% | 28% | 18% |
| Graph stage | 40% | 72% | 58% |
| MIO right | 16% | 32% | 24% |
| Bottom dock | 8% | 40% | 22% |

## Collapse Behavior

- Collapsed panels: `collapsedSize={0}`, icon recall on rail
- Graph stage: **non-collapsible**
- Mission strip: **non-resizable**, 56px fixed height

## Multi-Monitor (Phase 3)

`window.open` secondary surface with shared `BroadcastChannel('fusion-layout')` — spec only in Phase 0; single viewport implemented.

## Reset

`Shift+Alt+R` clears fusion layout keys (documented in keyboard UX).
