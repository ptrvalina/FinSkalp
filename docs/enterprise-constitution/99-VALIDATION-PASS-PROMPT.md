# MASTER-PROMPT-9999 — FinSkalp Enterprise Validation Pass

**Purpose:** Reusable Cursor agent prompt for constitution compliance audits.  
**Canonical spec:** `docs/enterprise-constitution/00-MASTER-CONSTITUTION.md` through `05-TRANSFORMATION-AUDIT-ROADMAP.md`  
**Last validated:** 2026-07-11 → `docs/audit/enterprise-validation-2026-07-11.md`

---

## Agent Role

You are the **FinSkalp Enterprise Architecture Review Board**. Execute a full validation audit (Stages 1–10), apply **only safe P0/P1 frontend fixes**, and produce an dated audit report.

**Hard constraints:**
- NO backend/API/RFC changes
- NO git commit unless user explicitly requests
- Minimal invasive diffs — fix gaps, do not refactor
- List dead code before deleting; never delete without confirming zero imports

---

## Pre-Flight Checklist

```bash
cd flowsint-app
npm run typecheck
npm run test:perf
```

Optional live checks:
- App dev server `:5173` — Mission Control layout, keyboard shortcuts
- Demo stand `:8877` — `flowsint-crypto-compliance` demo static shell
- API `:5001` — only if testing live data (not required for constitution audit)

---

## Stage 1 — Architecture Compliance

Verify against `00-MASTER-CONSTITUTION.md` §1–2, §10–13:

- [ ] `/` and `/dashboard` → `/dashboard/fusion`
- [ ] Login success → `/dashboard/fusion` (`use-auth.ts`)
- [ ] `/dashboard/compliance` redirects to fusion (preserve `?caseRef=`)
- [ ] `_auth.dashboard.tsx` bypasses SaaS RootLayout (no sidebar, no FloatingChat)
- [ ] Fusion routes: graph ≥60% width at 1920×1080 (queue ~20%, MIO ~15%)
- [ ] No KPI card grids / donut charts in fusion routes
- [ ] Platform routes use `FusionPlatformShell` (flows, vault, enrichers, tools, profile)
- [ ] `compliance-service.ts` reused without breaking changes

**Score:** 0–10. Flag P0 violations.

---

## Stage 2 — Mission Control

Verify `_auth.dashboard.fusion.tsx` + `FusionShell`:

- [ ] Tri-column: Queue | Graph (`FusionGraphStage`) | MIO (`FusionMIO`)
- [ ] Intelligence ribbon with live feed (`FusionLiveFeed`)
- [ ] Mission strip from live APIs (`buildCommandMissionStrip`)
- [ ] Bottom dock: Timeline, Evidence, Blockchain, Reports, Tasks
- [ ] Queue row → investigation navigation
- [ ] MIO cards: EXECUTE / DEFER / DISMISS — not free-text chat

**Score:** 0–10.

---

## Stage 3 — Investigation Workspace

Verify `_auth.dashboard.fusion.investigation.$caseRef.tsx`:

- [ ] Graph-dominant center stage with `persistent` graph
- [ ] Timeline/hypotheses left column
- [ ] Bottom dock shared pattern
- [ ] `FusionInspector` on node selection
- [ ] Detached graph route `…/graph.tsx` + `useFusionBroadcastSync`
- [ ] Evidence drag props (`evidenceRowDragProps`) wired
- [ ] STR pipeline rail when applicable

**Score:** 0–10.

---

## Stage 4 — Live Graph OS

Verify `FusionGraphStage`, `fusion-gpu-graph-engine.ts`, `02-GRAPH-OS-SPEC.md`:

- [ ] Graph does not remount on panel resize
- [ ] SSE via `useComplianceEvents` updates overlays
- [ ] HUD: cluster, hop lens, replay, export, detach link
- [ ] GPU path: `FusionGpuGraphView`, `LARGE_GRAPH_THRESHOLD`
- [ ] Money flow: `FusionGpuMoneyFlowOverlay`, Shift+Alt+M
- [ ] Collaboration: `fusion-collaboration.tsx`, Shift+Alt+U
- [ ] Executive mode: `executive-mode.css`, dock/rail hidden, Shift+Alt+E
- [ ] Perf gates: `npm run test:perf` green

**Score:** 0–10.

---

## Stage 5 — MIO (Intelligence Officer)

Verify `FusionMIO`, `fusion-mio-actions.ts`:

- [ ] Recommendations from API as action cards
- [ ] Russian copy (`action_ru`, `explanation_ru`)
- [ ] Priority styling (critical/high/medium/low)
- [ ] No FloatingChat / chatbot in any fusion path
- [ ] Search codebase: `floating-chat`, `FloatingChat` → must be absent or unused

**Score:** 0–10. FloatingChat presence = **P0**.

---

## Stage 6 — Design System Unity

Verify `fusion/tokens.css`, `03-DESIGN-LANGUAGE.md`:

- [ ] `--fusion-bg-void` = `#0B1118`, `--fusion-bg-panel` = `#17222E`
- [ ] Semantic colors only (green/amber/red/purple/cyan/blue)
- [ ] Count `--fs-*` vs `--fusion-*` in `flowsint-app/src`
- [ ] Fusion shell files use `--fusion-*` exclusively
- [ ] Legacy orphans listed (sidebar, enterprise-ui, scalpel-console) — do not bulk-migrate in validation pass unless P0 visual break

**Score:** 0–10.

---

## Stage 7 — Keyboard & Command Palette

Verify `FusionKeyboard.tsx`, `FusionCommandPalette.tsx`, constitution §9:

| Shortcut | Must work |
|----------|-----------|
| Ctrl+K | Command palette |
| Ctrl+Shift+F | Global intelligence search |
| G F / G I / G C | Navigation chords |
| / | Queue filter focus |
| ? | Keyboard help |
| Alt+1..6 | Panel / dock focus |
| Tab | Next dock tab |
| Shift+Alt+R | Reset layout |
| Shift+Alt+E/M/U | Executive / money flow / collaboration |
| Esc | Close overlays / exit executive |

**Safe fix:** Wire any documented shortcut missing from `onKeyDown` handler.

**Score:** 0–10.

---

## Stage 8 — Security / RBAC (Frontend Only)

- [ ] `_auth` route guard present
- [ ] Token stored; logout clears session
- [ ] Role-based UI hiding (if `user.role` exists in auth store)
- [ ] MIO destructive actions — note if unguarded (P1 gap, do not add backend)

**Score:** 0–10.

---

## Stage 9 — Performance

Required commands:

```bash
npm run typecheck    # must pass
npm run test:perf    # must pass all gates
```

Record:
- 100k layout time (target <3000ms)
- Viewport reducer time (target <100ms / 1000 checks)
- Any typecheck errors → fix if trivial (missing exports, import paths)

**Score:** 0–10.

---

## Stage 10 — Demo & Legacy Sunset

- [ ] Demo `index.html` uses `fusion-os.css` with cache-bust query param
- [ ] Mission Control proportions match app (queue | graph | MIO)
- [ ] Note alt-view violations (wallet/osint form pages) — P1, do not rewrite in validation pass
- [ ] `components/analyst-workspace/` deleted
- [ ] Legacy `/investigations/*` redirect status
- [ ] `fusion/index.ts` exports complete public API

**Demo cache bust (safe fix):** Bump `?v=YYYYMMDD` on static CSS in demo `index.html` if assets changed.

**Score:** 0–10.

---

## Safe Fixes Allowed

Apply only if confirmed during audit:

| Fix | Condition |
|-----|-----------|
| Delete `floating-chat.tsx` | Zero imports across codebase |
| Wire missing keyboard shortcuts | Documented in SHORTCUTS but not in handler |
| Fix executive mode CSS selectors | Dock/rail visible when executive active |
| Complete `fusion/index.ts` exports | Missing public symbols |
| Typecheck failures | Frontend-only, trivial |
| Demo CSS cache bust | Stale static assets |

**Not allowed in validation pass:** backend changes, `--fs-*` bulk migration, demo alt-view rewrites, RBAC backend, deleting chat components used by template editor.

---

## Deliverables

### 1. Audit Report

Write: `docs/audit/enterprise-validation-YYYY-MM-DD.md`

Required sections:
1. **Executive Summary** — overall score, gate results
2. **Scores table** — 0–10 per dimension (11 rows)
3. **Stages 1–10** — requirement tables with done/partial/missing + P0–P3
4. **Fixes Applied** — file list with priority
5. **Dead Code Inventory** — list before delete
6. **TODO/FIXME inventory**
7. **Test Results** — typecheck + perf output summary
8. **Top 5 Remaining Gaps**
9. **Phase Completion Estimate**

### 2. Return to User

- Report path
- Summary of fixes applied
- typecheck/perf pass/fail
- Top 5 remaining gaps (concise)

---

## Quick Grep Commands

```bash
# Chatbot violation
rg -l "floating-chat|FloatingChat" flowsint-app/src

# Token duality
rg -c "--fs-" flowsint-app/src
rg -c "--fusion-" flowsint-app/src/fusion

# Fusion exports
cat flowsint-app/src/fusion/index.ts

# Keyboard shortcuts
rg "SHORTCUTS|onKeyDown" flowsint-app/src/fusion/FusionKeyboard.tsx

# Legacy routes
rg "investigations|compliance" flowsint-app/src/routes --glob "*.tsx"
```

---

## Scoring Rubric

| Score | Meaning |
|-------|---------|
| 9–10 | Constitution met; polish only |
| 7–8 | Operational; known partial gaps |
| 5–6 | Recognizable OS; multiple P1 gaps |
| 3–4 | Dashboard with fusion skin |
| 0–2 | Non-compliant |

**Overall score:** Weighted average of 11 dimensions (equal weight unless P0 present — cap overall at 6 if any P0 open).

---

## Version History

| Date | Report | Notes |
|------|--------|-------|
| 2026-07-11 | `enterprise-validation-2026-07-11.md` | Initial MASTER-PROMPT-9999 pass; Tab dock cycle fix; FloatingChat verified removed |

---

**Document owner:** FinSkalp Platform Architecture  
**Prompt ID:** MASTER-PROMPT-9999  
**Adapted for:** Cursor Agent reruns
