# Operational Workspace Concept

## Definition

An **operational workspace** is a full-viewport instrument panel where:

- The analyst never loses spatial context
- Panels are tools, not pages
- Data arrives live and annotates the canvas
- Layout is personal but recoverable

## Workspace Modes

### Command Mode (`/dashboard/fusion`)

National cyber-fusion posture. Four zones (see `10-command-center.md`). Graph appears as Zone B preview — animated, not static thumbnail.

### Investigation Mode (`/dashboard/fusion/investigation/:caseRef`)

Single-case deep dive. Layout:

```
┌──Rail──┬─Timeline/Evidence──┬──────GRAPH STAGE──────┬─MIO──┐
│  48px  │      18%           │        58%            │ 24%  │
│        │                    │   (never unmounts)    │      │
├────────┴────────────────────┴───────────────────────┴──────┤
│                    BOTTOM DOCK (resizable)                  │
│         Evidence · Wallets · Reports · OSINT                │
└─────────────────────────────────────────────────────────────┘
│              MISSION STRIP (14 fields, full width)          │
└─────────────────────────────────────────────────────────────┘
```

### Legacy Mode

Existing `RootLayout` + sidebar. Accessible via rail LEGACY link and sidebar "Fusion Center" reverse link.

## Zone Semantics

| Zone | Operational color accent | Content |
|------|-------------------------|---------|
| Alpha | Blue | Threat / queue ingress |
| Bravo | Gray | Situation grid |
| Charlie | Green/Yellow/Red | Graph / risk |
| Delta | Blue | Intelligence feed |

## Panel Lifecycle

1. **Collapsed** — rail icon only, 0px width
2. **Docked** — resizable split in zone
3. **Expanded** — temporary full-zone (slide over siblings)
4. **Pinned** — survives layout reset

No fifth state (modal) exists.

## Multi-Case Context

Switching cases via queue updates mission strip and graph data but **preserves dock tab selection** per case in `fusion-case-state-{caseRef}`.

## Operator Rhythm

1. Scan mission strip (2s)
2. Glance live feed ticker (peripheral)
3. Work graph center
4. Pull evidence from left dock
5. Act on MIO recommendation cards (right)
6. File from bottom dock reports tab
