# FinSkalp Enterprise Design Constitution v3.0

**Status:** CANONICAL — supersedes all prior fusion-design-system and enterprise-workspace specifications.

---

## Section 0 — Identity

FinSkalp is a **Financial Intelligence Operating System** — not a dashboard, not a web app, not a SaaS product shell.

Analysts operate inside a persistent intelligence workspace where the **graph is the operating surface** (60–70% of viewport, never reloads, evolves live). All other panels orbit the graph: queue, officer, timeline, evidence, blockchain, reports.

---

## Section 1 — Non-Negotiables

| Rule | Requirement |
|------|-------------|
| Graph as OS | Graph occupies 60–70% of workspace; survives route changes within mission; live sync |
| No dashboards | No card grids, KPI widgets, mega-stats, donut charts, decorative metrics |
| Mission Control default | Login lands on Mission Control — not overview pages |
| Drawers only | No inline forms in workspace; data entry via drawers/modals at edge |
| Intelligence Officer | Proactive recommendation cards — NOT a chatbot |
| Keyboard-first | Command palette `Ctrl+K`, chord navigation, workspace memory |
| Density | Target 80%+ information density; Palantir/Bloomberg operational tone |
| Backend safety | No breaking changes to APIs, RFC modules, or compliance services |

---

## Section 2 — Mission Control Layout (Chapter 3)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ INTELLIGENCE RIBBON — mission strip + live alerts/activity ticker         │
├────────────┬──────────────────────────────────────────────┬───────────────┤
│ MISSION    │ LIVE INTELLIGENCE GRAPH (60–70%)              │ INTELLIGENCE  │
│ QUEUE ~20% │ Dominant stage — never unmount on navigation  │ OFFICER ~15%  │
│ Cases +    │ ComplianceGraphView / FusionGraphStage        │ MIO cards     │
│ critical   │                                               │ not chat      │
├────────────┴──────────────────────────────────────────────┴───────────────┤
│ BOTTOM DOCK: Timeline │ Evidence │ Blockchain │ Reports │ Tasks          │
└──────────────────────────────────────────────────────────────────────────┘
```

Left rail (48px): section navigation only. No SaaS sidebar inside fusion routes.

---

## Section 3 — Investigation Workspace

Same graph-dominant principle. Timeline/hypotheses may occupy left column; bottom dock persists across tabs. MIO executes workflow actions (fuse, transition, screen, report).

Detached graph route syncs via `BroadcastChannel`. Graph never reloads on panel resize.

---

## Section 4 — Design Language

- **Tone:** Palantir/Bloomberg density — original, not copy
- **Surfaces:** void → deck → panel → interactive (4-level depth)
- **Color:** semantic only — no brand gradients, no neon overload
- **Typography:** Inter + IBM Plex Mono; uppercase micro-labels; tabular numerals
- **Motion:** 150–400ms functional transitions; respect `prefers-reduced-motion`

---

## Section 5 — Color Constitution

| Token role | Meaning |
|------------|---------|
| `--fusion-bg-void` `#0B1118` | Deepest background / graph canvas |
| `--fusion-bg-deck` `#111A24` | Shell deck, rail, strip |
| `--fusion-bg-panel` `#17222E` | Panel surfaces |
| `--fusion-bg-interactive` `#1E2B39` | Hover, focus, raised rows |
| Green | Verified / clear / nominal |
| Amber | Attention / pending / caution |
| Red | Risk / breach / critical |
| Purple | Intelligence / OSINT / fusion |
| Cyan | Blockchain / on-chain |
| Blue | System / navigation / active op |

Text hierarchy: 92% / 68% / 45% white opacity.

---

## Section 6 — Graph OS Rules

1. Graph instance persists for active case session
2. Live SSE events update overlays without full remount
3. Layers: entities, transactions, evidence links, cross-case links, alert highlights
4. HUD: cluster count, hop lens, replay, export PNG/SVG
5. Performance targets: paint <100ms; interaction 60fps to 10k nodes (Phase 2+)

**Deferred:** GPU million-node engine, money-flow particles, cinematic executive mode.

---

## Section 7 — Intelligence Officer (MIO)

- Surfaces API recommendations as actionable cards
- Priority-coded: critical / high / medium / low
- Actions: EXECUTE, DEFER, DISMISS — never free-text chat
- Russian UI strings for analyst-facing copy (`action_ru`, `explanation_ru`)

---

## Section 8 — Panel & Docking System

- Resizable panels with `autoSaveId` → localStorage workspace memory
- Bottom dock tabs: Timeline, Evidence, Blockchain, Reports, Tasks
- Pin/float/collapse on investigation panels
- Reset layout: `Shift+Alt+R`

---

## Section 9 — Keyboard & Command Palette

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Command palette |
| `G F` | Mission Control |
| `G I` | Last investigation |
| `G C` | Find case |
| `/` | Focus queue filter |
| `?` | Keyboard help |
| `Esc` | Close overlays |

Palette actions: Find Case, Focus Entity, Open Timeline, Mission Control, Reset Layout.

---

## Section 10 — Routing & Legacy

- Default: `/` → `/dashboard/fusion`
- Fusion routes bypass `RootLayout` (no SaaS sidebar, no floating chat)
- `/dashboard/compliance` → redirect to fusion (preserve `?caseRef=`)
- Platform routes (flows, vault, enrichers) retain legacy shell

---

## Section 11 — API Reuse Mandate

Reuse without modification:
- `compliance-service.ts`
- `ComplianceGraphView` / `FusionGraphStage`
- `useComplianceEvents`
- Inbox, graph, timeline, recommendations, workspace state endpoints

---

## Section 12 — Quality Gate

Before merge:
- [ ] No KPI card grids in fusion routes
- [ ] Graph ≥60% width on Mission Control at 1920×1080
- [ ] Constitution palette in `fusion/tokens.css`
- [ ] `npm run typecheck` passes
- [ ] Demo `:8877` deck tokens aligned

---

## Section 13 — Final Directive (Absolute)

> FinSkalp is a Financial Intelligence Operating System — NOT a dashboard/web app.
> - Graph IS the OS (60-70% workspace, never reloads, evolves live)
> - No pages/dashboards/cards/KPI widgets
> - Mission Control on login (queue left, massive live graph center, AI Officer right, timeline/evidence/blockchain/reports bottom)
> - Design language: Palantir/Bloomberg density, original not copy
> - Colors: bg `#0B1118`, panels `#17222E`, semantic only (green/amber/red/purple/cyan/blue)
> - No forms in workspace (drawers only)
> - Intelligence Officer not chatbot
> - Docking panels, command palette Ctrl+K, keyboard-first, workspace memory
> - DO NOT break backend/APIs/RFC modules

**Document owner:** FinSkalp Platform Architecture  
**Version:** 3.0  
**Effective:** 2026-07-11
