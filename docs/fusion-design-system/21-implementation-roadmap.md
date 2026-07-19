# Implementation Roadmap

## Zero-Breaking Principle

Every phase is additive. Legacy routes remain until explicit deletion phase.

---

## Phase 0 — Foundation (Weeks 1–2) ✅

**Done:**
- [x] `docs/fusion-design-system/` complete spec (22 files)
- [x] `flowsint-app/src/fusion/` CSS tokens + components
- [x] Routes `/dashboard/fusion` + `/dashboard/fusion/investigation/:caseRef`
- [x] Sidebar "Fusion Center" entry
- [x] `FusionGraphStage` + graph HUD + risk propagation props
- [x] `npm run typecheck` pass

---

## Phase 1 — Data Density (Weeks 3–4) ✅

- [x] Wire all 14 mission strip fields to live APIs (`fusion-mission-data.ts`)
- [x] Virtualized `FusionDataGrid` with sort/filter/pin/keyboard nav
- [x] Case queue drag reorder (`reorderCaseQueue`)
- [x] Fusion keyboard UX (`?`, `g` chords, `/`, Escape) in `FusionShell`
- [x] `FusionMIO` execute actions (`fuseCase`, `transitionCase`, `screenWallet`, report PDF)

---

## Phase 2 — Graph Excellence (Weeks 5–6) ✅

- [x] Cluster-aware HUD chip from graph payload (`FusionGraphStage`)
- [x] Cross-case link overlay (`getCrossCaseGraphLinks` on investigation route)
- [x] Temporal replay in `ComplianceGraphView` (investigation / detached graph)
- [x] Timeline ↔ graph bidirectional highlight (`buildTimelineNodeMap`, investigation route)
- [x] Graph snapshot export PNG/SVG (`exportGraphSnapshot` in graph HUD)
- [x] Hop-distance lens filter (BFS client-side, HUD select ≤N hops)

**Migrate:** `analyst-workspace-shell.tsx` graph tab → redirect to fusion investigation  
**Delete candidate:** `graph-insights-panel.tsx`

---

## Phase 3 — Multi-Monitor + MIO Execute (Weeks 7–8) ✅

- [x] Detached graph route `/dashboard/fusion/investigation/:caseRef/graph`
- [x] `BroadcastChannel` sync (`useFusionBroadcastSync`, channel `finskalp-fusion-{caseRef}`)
- [x] MIO action cards wire `fuseCase`, `transitionCase`, `screenWallet`, report PDF
- [x] STR pipeline visual progress rail (`FusionStrPipeline` in `FusionShell`, maps `workflow_status`)
- [x] Post-login default redirect → `/dashboard/fusion`

**Migrate:** `investigation-copilot-panel.tsx` → absorbed by `FusionMIO`  
**Delete candidate:** `situation-awareness-grid.tsx`

---

## Phase 4 — Legacy Sunset (Weeks 9–12) — DONE (file deletion)

- [x] Default login redirect → `/dashboard/fusion`
- [x] `/dashboard/compliance` → redirect to fusion (preserves `?caseRef=`)
- [x] Investigation workspace with linked case → redirect to fusion investigation
- [x] Sidebar: Fusion Center primary; legacy nav removed
- [x] Deleted legacy UI:
  - `compliance-page.tsx`
  - `analyst-workspace/` (shell + panels; wallets/reports → `fusion/panels/`)
  - `enterprise/*` pre-fusion panels (queue, mission strip, copilot, grid, operator-events, sla, data-table)
  - `dashboard-page.tsx` card overview
  - `docs/enterprise-workspace/` (superseded by `fusion-design-system/`)
- [ ] Remove `--fs-*` tokens where unused (optional cleanup)
- [ ] FusionRail-only layout for all fusion routes (hide legacy sidebar chrome)

**Keep forever:**
- `compliance-service.ts`
- `ComplianceGraphView` (fusion-enhanced)
- Platform routes (flows, enrichers, vault)

---

## Deletion vs Migration Matrix

| Asset | Phase | Action |
|-------|-------|--------|
| `design-system/tokens.css` | 4 | Merge into `fusion/tokens.css` |
| `enterprise-ui.tsx` | 4 | Delete |
| `sidebar.tsx` SaaS nav | 4 | Fusion-only rail in shell |
| `root.layout.tsx` | 3 | Bypass for fusion routes |
| `floating-chat` | 4 | Remove from fusion |
| `compliance-graph-view.tsx` | — | **Keep** (enhance only) |

---

## Risk Register

| Risk | Mitigation |
|------|------------|
| Analyst training | Parallel routes 8+ weeks |
| Layout localStorage corruption | Shift+Alt+R reset |
| SSE duplicate connections | Single hook per shell |
| Typecheck regressions | CI gate on fusion imports only |

---

## Success Metrics

- Investigation workspace: graph visible within 100ms of route paint
- Zero API changes across all phases
- Legacy compliance route functional until Phase 4 file deletion

---

## Test URLs (local dev)

| URL | Expected |
|-----|----------|
| `/dashboard/fusion` | Command center + STR pipeline |
| `/dashboard/fusion/investigation/FSK-BF-2026-0711-001` | Investigation + timeline↔graph |
| `/dashboard/fusion/investigation/FSK-BF-2026-0711-001/graph` | Detached graph + BroadcastChannel sync |
| `/dashboard/compliance?caseRef=FSK-BF-2026-0711-001` | Redirect to fusion investigation |
| `/dashboard/compliance` | Redirect to `/dashboard/fusion` |
