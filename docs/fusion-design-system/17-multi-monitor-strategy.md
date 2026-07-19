# Multi-Monitor Strategy

## Phase 0 (Current)

Single viewport. `FusionShell` uses `position: fixed; inset: 0; z-index: 50` to supersede legacy chrome.

## Phase 3 Target

### Secondary Window

1. Analyst clicks DETACH on graph or feed panel
2. `window.open('/dashboard/fusion/detached?panel=graph&caseRef=...')`
3. `BroadcastChannel('fusion-sync')` shares: caseRef, SSE events, graph pin state

### Layout Sync

| Channel message | Action |
|-----------------|--------|
| `case:change` | Both windows update mission strip |
| `graph:pin` | Sync pinned node IDs |
| `alert:pulse` | Mirror node pulse |

### Monitor Placement

`window.moveTo` with saved coordinates in `fusion-monitor-geometry`.

## Use Cases

| Monitor 1 | Monitor 2 |
|-----------|-----------|
| Graph full screen | Timeline + MIO |
| Command center | Investigation workspace |
| Live feed wall | Queue triage |

## Constraints

- No Electron-specific APIs required (web-first)
- Popup blockers: fallback to dock-expand (slide full zone)

## Phase 0 Stub

Detach button shows tooltip: `MULTI-MONITOR — PHASE 3`
