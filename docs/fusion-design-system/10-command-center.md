# Command Center

## Route

`/dashboard/fusion`

## Concept

National cyber-fusion **command floor** — four operational zones, no card grid.

```
┌────────────────────────────────────────────────────────────┐
│ MISSION STRIP — national posture (workflow stats, SLA)      │
├──────────────────────┬─────────────────────────────────────┤
│ ZONE ALPHA           │ ZONE BRAVO                          │
│ Threat Queue Ingress │ Situation Awareness Grid            │
│ (FusionDataGrid)     │ (pipeline counts, SLA breaches)     │
├──────────────────────┼─────────────────────────────────────┤
│ ZONE CHARLIE         │ ZONE DELTA                          │
│ Global Graph Preview │ Live Intelligence Feed              │
│ (FusionGraphStage)   │ (FusionLiveFeed)                    │
└──────────────────────┴─────────────────────────────────────┘
```

## Zone Data

| Zone | APIs |
|------|------|
| Alpha | `listInbox`, `listCases` |
| Bravo | `getWorkflowStats` |
| Charlie | First inbox case graph or empty |
| Delta | `useComplianceEvents` |

## Queue Interaction

Row click → navigate `/dashboard/fusion/investigation/{caseRef}`

## National Posture Strip Fields

Uses workflow stats + inbox counts — missing fields `—`.

## No Widgets

Zone Bravo shows monospace pipeline counts in rows, not donut charts:

```
PIPELINE  new: 12 │ fusion: 8 │ review: 3 │ filed: 41
SLA       breached: 2 │ due <4h: 5
```

## Graph Preview

Charlie zone uses first high-priority inbox case. Graph height: 100% of zone. `compact={true}` for preview density.
