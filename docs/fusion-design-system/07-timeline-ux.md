# Timeline UX

## Role

Left-zone **mission chronology** — not a social feed. Events are evidentiary milestones.

## Data

`getCaseTimeline(caseRef)` → `events[]` with `event_type`, `occurred_at`, `actor`, `payload`.

## Visual

```
09:41:22  FUSION_COMPLETE    operator:system
          └─ 14 entities resolved · confidence 0.82

09:38:01  WALLET_SCREENED    operator:analyst-7
          └─ 0x7a3…f2 · risk 78 · chain ETH
```

## Density

- Row height: 32px collapsed, 48px expanded
- Timestamp: IBM Plex Mono 10px `--fusion-text-tertiary`
- Event type: 9px uppercase tracking 0.14em
- Actor: mono secondary

## Interactions

| Action | Result |
|--------|--------|
| Click event | Highlight related graph nodes (if payload contains entity) |
| Hover | Show payload key fields (max 3) |
| Scroll | Virtualized list (Phase 2) |

## Sync with Graph Replay

When timeline event has `occurred_at` matching graph temporal data, clicking event sets replay slider index.

## Empty State

`AWAITING TIMELINE EVENTS` — mono, centered, no illustration.
