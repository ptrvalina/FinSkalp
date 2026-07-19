# Information Operating Model

## Workspace Philosophy

FinSkalp treats **information as operational terrain**, not content to browse. Analysts do not "visit pages" — they **enter missions**. Each mission binds:

- A case reference (STR / alert / investigation)
- A live graph of entities and flows
- A queue position and SLA clock
- Evidence chain and timeline state
- MIO recommendations tied to workflow stage

The workspace **remembers** panel sizes, pins, last case, and filter focus via localStorage.

---

## Mission Model

| Mode | Route | Purpose |
|------|-------|---------|
| Mission Control | `/dashboard/fusion` | National posture — queue ingress, graph preview, MIO triage |
| Investigation | `/dashboard/fusion/investigation/:caseRef` | Deep case work — full graph, timeline sync, dock |
| Detached Graph | `…/graph` | Multi-monitor graph mirror with BroadcastChannel sync |

Mission strip fields bind to live APIs (`fusion-mission-data.ts`). Missing data displays `—`, never placeholder widgets.

---

## Layout ASCII — Mission Control v3

```
                    ┌─ Intelligence Ribbon ─────────────────────────────┐
                    │ [Objective][Threat][Status]… │ LIVE: alert ticker │
                    └───────────────────────────────────────────────────┘
┌──┐ ┌─ Queue ─────┐ ┌─ Graph OS ─────────────────────────┐ ┌─ MIO ────┐
│R │ │ FSK-…  CRIT │ │                                     │ │ EXECUTE  │
│a │ │ FSK-…  HIGH │ │     ●───●───●                       │ │ Screen   │
│i │ │ …           │ │      \   /                          │ │ wallet   │
│l │ │             │ │       ●                             │ │          │
└──┘ └─────────────┘ └─────────────────────────────────────┘ └──────────┘
      ┌─ Dock ──────────────────────────────────────────────────────────┐
      │ Timeline │ Evidence │ Blockchain │ Reports │ Tasks              │
      └─────────────────────────────────────────────────────────────────┘
```

Rail (left): Command · Investigate · Platform links — 48px icon strip.

---

## Information Density Target

**80%+** of panel area conveys operational data (rows, graph, feed lines, strip cells). Forbidden:

- Hero banners
- Empty-state illustrations occupying >20% viewport
- Summary cards with single large numbers
- Chart junk (pies, donuts, gauges) unless encoding time-series in graph HUD

---

## Analyst Workflow Loop

1. **Ingress** — Mission Control queue surfaces critical cases
2. **Select** — Row click → investigation route; graph loads persistent
3. **Orient** — Timeline ↔ graph bidirectional highlight
4. **Act** — MIO EXECUTE (fuse, screen, transition, report)
5. **File** — STR pipeline rail tracks workflow to SAR

Russian copy preserved for analyst-facing strings per 115-FZ operational context.

---

## Multi-Monitor Strategy (Future)

Primary: investigation workspace. Secondary: detached graph. Tertiary: executive read-only (Phase 7 — deferred).
