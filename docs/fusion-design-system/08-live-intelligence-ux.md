# Live Intelligence UX

## Source

`useComplianceEvents` — SSE `/api/compliance/events/stream`

## FusionLiveFeed

Horizontal ticker + vertical scroll panel variants.

### Ticker Rules

- Max 50 events in memory (existing hook default)
- New events: `fusion-feed-enter` animation (opacity 0→1, 300ms)
- Severity maps to operational color left border (4px)
- Text: `text_ru` or `operator_event_type`

### Severity → Color

| Severity | Token |
|----------|-------|
| critical | `--fusion-ops-red` |
| warning | `--fusion-ops-orange` |
| info | `--fusion-ops-blue` |
| default | `--fusion-text-secondary` |

## Graph Integration

Filtered `graphAlerts` subset triggers node pulse (see graph engine doc). Feed and graph share SSE — no duplicate connections per surface.

## Catalog

`getOperatorEventCatalog` loaded once; MIO uses catalog labels for unknown event types.

## Fade-In Discipline

New intelligence never pops — always 300ms fade + 4px slide from top. Reduced motion: fade only.

## Command Center Placement

Zone Delta: full-height feed with auto-scroll paused on hover.

## Investigation Placement

Mission strip slot `INTELLIGENCE` shows last critical event summary; full feed in MIO tab.
