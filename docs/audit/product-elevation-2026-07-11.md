# FinSkalp — Absolute Product Elevation Audit

**Date:** 2026-07-11  
**Role:** CPO · Principal UX · Visual · Software Architect · Investigation Analyst · Performance Engineer  
**Scope:** `flowsint-app` (:5173) + demo `:8877` + constitution v3  
**Rule:** Analysis only — no code in this document phase

---

## Executive Summary

FinSkalp has a **credible Fusion OS core** (Mission Control + Investigation) but the product still reads as **two products stitched together**: an intelligence operating system (fusion routes) and a conventional SaaS builder (Flow Architect, Schema Architect, enricher editor). Constitution compliance is ~8.5/10 on fusion paths; **whole-product maturity is ~7.8/10**.

**Primary elevation lever:** unify visual/UX language on platform routes, deepen graph-first actions, polish empty/error/loading states, complete Phase 3 MIO depth — **without touching backend/RFC/API**.

---

## 1. Screen Map

| Route | Shell | Graph-centric | Density est. | Investigation value | Verdict |
|-------|-------|---------------|--------------|---------------------|---------|
| `/login` | None (v3 styled) | N | 40% | Entry | **Keep** — polish error UX |
| `/dashboard/fusion` | FusionShell | **Y** (67%) | 85% | Mission Control | **Core** — reference screen |
| `/dashboard/fusion/investigation/$caseRef` | FusionShell | **Y** (68%) | 88% | Primary workspace | **Core** — reference screen |
| `/dashboard/fusion/investigation/$caseRef/graph` | FusionShell | **Y** (100%) | 90% | Detached graph | **Keep** |
| `/dashboard/compliance` | Redirect | — | — | Legacy entry | **Keep** redirect |
| `/dashboard/tools` | FusionPlatformShell | N | 75% | Scalpel catalog | **Keep** — token-unified |
| `/dashboard/vault` | FusionPlatformShell | N | 70% | Secrets | **Keep** |
| `/dashboard/profile` | FusionPlatformShell | N | 65% | Operator profile | **Keep** |
| `/dashboard/flows/` | FusionPlatformShell | N | 60% | Flow list | **Merge feel** with fusion lists |
| `/dashboard/flows/$flowId` | FusionPlatformShell | N | 55% | Flow editor | **SaaS leak** — inner editor shadcn |
| `/dashboard/custom-types/*` | FusionPlatformShell | N | 50% | Schema editor | **SaaS leak** — bg-background inside |
| `/dashboard/enrichers/*` | FusionPlatformShell | N | 55% | Template editor | **SaaS leak** |
| `/dashboard/investigations/*/graph` | FusionPlatformShell | Partial | 60% | Sketch graph | **Redirect** when case mapped |
| `/dashboard/investigations/*/analysis` | FusionPlatformShell | Partial | 60% | Analysis | **Platform** — OK |
| Demo `:8877` dashboard | fusion-os shell | **Y** | 80% | Demo MC | **Core demo** |
| Demo wallet/osint/registries | Drawer overlay | N | 70% | Intel tools | **Fixed** — drawers not pages |

**Surfaces:** 3 tiers — **Tier A** Fusion OS (investigation), **Tier B** Fusion Platform (lists), **Tier C** Legacy editors (shadcn interior).

---

## 2. Component Map

```
flowsint-app/src/
├── fusion/                    ← CANONICAL OS (54 files)
│   ├── Shell: FusionShell, FusionPlatformShell, FusionRail
│   ├── Workspace: FusionGraphStage, FusionDock, FusionMIO, FusionInspector
│   ├── Intelligence: FusionCommandPalette, FusionGlobalSearch, FusionLiveFeed
│   ├── Graph: FusionGpuGraphView, fusion-gpu-graph-engine, compliance-graph-view (legacy enhanced)
│   ├── Sync: fusion-sync-bus, fusion-broadcast-sync, fusion-collaboration
│   └── CSS: tokens.css, panels.css, graph-chrome.css, executive-mode.css, motion.css
├── components/compliance/       ← API + graph (KEEP)
│   ├── compliance-service.ts    ← immutable API client
│   └── compliance-graph-view.tsx ← ReactFlow path (@legacy enhanced)
├── components/layout/           ← LEGACY SaaS (bypassed on /dashboard/*)
│   ├── sidebar.tsx, root.layout.tsx, page-layout.tsx, top-navbar.tsx
├── components/enterprise/       ← LEGACY cards (enterprise-ui.tsx) — migrated tokens, not used in fusion
├── components/ui/               ← shadcn primitives (used inside platform editors)
└── hooks/
    ├── use-fusion-permissions.ts ← RBAC UI (new)
    └── use-compliance-events.ts  ← SSE live feed
```

**Dependency rule violated:** Platform editors import shadcn + `bg-background` inside `FusionPlatformShell` → visual tier break.

---

## 3. User Scenario Map

| Scenario | Steps today | Context lost? | Target |
|----------|-------------|---------------|--------|
| Login → operate | 1 click → fusion | No | ✅ |
| Pick case from queue | Click row → investigation | No | ✅ |
| Fuse case | MIO EXECUTE or dock | No | ✅ |
| Screen wallet | MIO → API | Minimal | ✅ |
| Generate report | Ctrl+R / MIO / dock | No | ✅ |
| Timeline → entity | Click event → graph highlight | Partial replay | ⚠️ improved |
| Evidence → graph | Drag row → drop graph | Yes + toast | ✅ |
| Global search entity | Ctrl+Shift+F | Opens case | ✅ |
| Edit flow pipeline | Navigate to /flows/$id | **Yes** — leaves OS | ⚠️ acceptable (platform) |
| Configure enricher | /enrichers | **Yes** — SaaS UI | ⚠️ platform tier |
| Detach graph | HUD link → new window | Sync via BroadcastChannel | ✅ |
| Executive briefing | Shift+Alt+E / Cinematic | No | ✅ |
| Read-only analyst | MIO hides EXECUTE | No | ✅ |

**Critical path (investigation-only):** 8/10 — analyst can stay in fusion without page hopping.

---

## 4. Data Flow Map

```
API :5001 (compliance-service.ts)
├── listInbox / getCase / getGraph ──→ FusionGraphStage, FusionInspector
├── getRecommendations ──────────────→ FusionMIO (buildMioCards)
├── workflow transitions / fuse ─────→ mutations → query invalidation
├── getRbacEffective ────────────────→ useFusionPermissions
├── SSE (use-compliance-events) ───→ FusionLiveFeed, graphAlerts
└── reports / evidence / timeline ─→ FusionDock tabs

Local persistence
├── fusion-layout-storage ─────────→ panel sizes, pins
├── fusion-layout-presets ─────────→ named layouts, GPU flag, queue width
└── fusion-sync-bus ───────────────→ live pause, dock tab, executive mode

Cross-window
└── fusion-broadcast-sync (BroadcastChannel) ─→ detached graph ↔ investigation
```

**Gap:** Graph query remounts on `caseRef` change (expected); no global graph store across cases (constitution "never reloads" = within session per case — **partial**).

---

## 5. Investigation Flow Map

```
Mission Control                    Investigation Workspace
┌─────────┬──────────┬─────┐      ┌──────────┬────────────┬─────┐
│ Queue   │ Graph    │ MIO │      │ Timeline │ Graph      │ MIO │
│ select  │ preview  │     │ ──→  │ scrub    │ dominant   │     │
└─────────┴──────────┴─────┘      └──────────┴────────────┴─────┘
     │                                   │
     └──────── caseRef ──────────────────┘
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
   FusionInspector      FusionDock (evidence, reports, chain)
         ▲                     │
         └──── node select ────┘
              ▲
              └── timeline click / replayIndex / SSE alert
```

**Sync status:** node select ↔ inspector ✅ · timeline click → highlight ✅ · replay scrub → cumulative highlight ✅ · evidence drag → node ✅ · MIO → workflow API ✅

---

## 6. Twelve Criteria Assessment

### 1. Visual Cohesion — **7/10** (target 10)

| Finding | Severity |
|---------|----------|
| Fusion routes: unified void/panel/mono | ✅ Strong |
| Platform list routes: fusion chrome + fusion lists | ✅ Good |
| Platform editors: shadcn `bg-background`, rounded-xl inside shell | **P1 break** |
| Login v3 void; register may still be default | **P2** |
| Demo `:8877` aligned with fusion-os.css | ✅ Good |

**Fix:** Restyle editor interiors to `--fusion-bg-*` + remove card shadows; single list component pattern.

---

### 2. Investigation Flow — **8.5/10**

Analyst completes fuse/screen/report without leaving investigation route. Platform config is intentionally separate.

**Fix:** Deep-link from MIO "configure collector" → tools drawer overlay (optional P2).

---

### 3. Graph First — **7.5/10**

Most actions reachable from graph context (select → inspector, drag evidence, HUD export, cinematic).

**Gaps:** Wallet screening still MIO-driven; OSINT not in-graph layer toggle; cluster filter HUD partial.

---

### 4. Context Preservation — **8/10**

Queue selection, last case (`loadLastCaseRef`), layout presets, broadcast sync preserve context.

**Gaps:** Switching platform route loses case selection in rail highlight; no "return to investigation" breadcrumb on platform pages.

---

### 5. Information Density — **8.5/10** (fusion) / **6/10** (editors)

Mission Control and Investigation exceed 80% operational pixels.

**Violators:** Flow/custom-type editors ~50% whitespace; profile page sparse.

---

### 6. Cognitive Load — **8/10**

Keyboard map documented; command palette; MIO cards with EXECUTE/DEFER.

**Gaps:** Dock 5 tabs unlabeled icons for new users; hop lens requires HUD discovery.

---

### 7. Enterprise Feeling — **8/10**

Regulator/bank would trust fusion investigation surfaces. Platform editors undermine "one product" story in demo walkthrough.

---

### 8. Motion — **7.5/10**

| Motion | Status |
|--------|--------|
| SSE risk pulse | ✅ |
| Money flow particles | ✅ (toggle) |
| Node appear (complianceNodeIn) | ✅ |
| Replay highlight | ✅ |
| Graph expansion live | Partial (query refetch not morph) |
| Decorative | None found in fusion |

---

### 9. Data Integrity — **7/10**

| Issue | Example |
|-------|---------|
| Mixed EN/RU | HUD English, MIO Russian — intentional but inconsistent |
| Entity labels | API `label` vs `kind` display varies |
| Case vs investigation id | Mapped in routes — OK |

**Fix:** Glossary doc + HUD microcopy pass (RU or EN lock).

---

### 10. Performance — **9/10**

`test:perf` 100k layout ~470ms; GPU auto at 500+ (investigation) / 1500+ (command).

**Watch:** ReactFlow path unbenchmarked in CI; money flow canvas capped 1200 edges ✅.

---

### 11. Accessibility — **6.5/10**

| Check | Status |
|-------|--------|
| Keyboard nav fusion | ✅ Strong |
| Focus rings | Partial (custom chips) |
| Contrast void/panel | ✅ WCAG likely pass |
| Screen reader graph | ⚠️ `role="application"` only |
| Reduced motion | ✅ tokens.css |
| Multi-monitor | ✅ float panels |

---

### 12. Product Identity — **7.5/10**

Fusion OS is recognizable. shadcn editors + `components/ui/sidebar` remnants = React Admin echo.

---

## 7. Design Review (Per Screen)

| Screen | Needed? | Merge? | Reduce actions? | Mission Control? | Helps investigation? |
|--------|---------|--------|-------------------|------------------|----------------------|
| Mission Control | Yes | No | Queue filter `/` | **Yes** | Yes |
| Investigation | Yes | No | — | **Yes** | **Primary** |
| Detached graph | Yes | No | — | Yes | Yes |
| Tools/Scalpel | Yes | Drawer optional | Search only | Platform | Indirect |
| Vault | Yes | No | — | Platform | Indirect |
| Flows list | Yes | Could be fusion panel | New flow only | No | Pipeline config |
| Flow editor | Yes | No | — | No | Builder |
| Custom types | Yes | No | — | No | Schema |
| Profile | Yes | Merge into rail menu | — | No | Operator |
| Login | Yes | No | — | Entry | Entry |

---

## 8. Graph Excellence Checklist

| Capability | Status | Priority |
|------------|--------|----------|
| Readability (glyphs, labels) | Partial — ReactFlow generic | P2 |
| Filtering (hop lens, layers) | Partial | P2 |
| Performance (GPU path) | Strong | — |
| Clustering HUD | Partial | P2 |
| Semantic animation | Strong | — |
| In-graph search | Ctrl+F palette | P2 node focus |
| Selection / inspector | Strong | — |
| Timeline sync | Good post-P1 | — |
| Money flow display | Strong | — |
| Live SSE update | Strong | — |
| Auto GPU threshold | Strong | — |

---

## 9. UI Consistency Gaps

| Element | Fusion OS | Platform | Action |
|---------|-----------|----------|--------|
| Spacing | `--fusion-space-*` | Mixed | P1 |
| Typography | fusion-text-* | shadcn text-sm | P1 editors |
| Colors | `--fusion-*` | `--fs-*` only in tokens.css aliases | ✅ migrated |
| Panels | FusionPanel | Card components | P1 |
| Empty states | fusion-text-micro | Mixed | P2 polish |
| Toasts | sonner | sonner | ✅ unify copy RU |
| Loading | text "ЗАГРУЗКА" | Skeleton shadcn | P2 fusion skeleton |

---

## 10. Legacy Cleanup Inventory (DO NOT DELETE — confirm first)

| Asset | Status | Recommendation |
|-------|--------|----------------|
| `components/layout/sidebar.tsx` | Unused on dashboard | **Archive** after grep zero imports |
| `components/layout/root.layout.tsx` | Unused on dashboard | **Archive** |
| `components/layout/page-layout.tsx` | Scalpel non-embedded only | **Keep** |
| `components/enterprise/enterprise-ui.tsx` | No fusion imports | **Archive** or migrate reports |
| `design-system/tokens.css` `--fs-*` | Alias layer | **Keep** until Phase 5 complete |
| `components/chat/*` | Enricher AI panel | **Keep** |
| `components/ui/sidebar.tsx` | shadcn | **Keep** for editors |
| `floating-chat.tsx` | Deleted | ✅ |
| `analyst-workspace/*` | Deleted | ✅ |

---

## 11. Product Polish Gaps

| Polish | Status | Priority |
|--------|--------|----------|
| Empty states with next action | Partial ("НЕТ РЕКОМЕНДАЦИЙ" OK; queue empty OK) | P2 |
| Error messages | toast.error generic | P2 contextual |
| Background process indicators | React Query isLoading scattered | P2 unified strip |
| Skeleton loading | FusionDataGrid text only | P2 fusion skeleton rows |
| User prefs persistence | Layout/GPU/presets | ✅ Strong |
| Notification style | sonner | ✅ |

---

## 12. Target Scorecard

| Criterion | Current | Target | Gap |
|-----------|---------|--------|-----|
| Visual Quality | 7.0 | 10 | Platform editor interiors |
| UX | 8.0 | 10 | Dock discoverability, return-to-case |
| Investigation Flow | 8.5 | 10 | Optional in-graph OSINT |
| Graph Experience | 8.0 | 10 | ReactFlow glyphs, layer toggles |
| Information Density | 8.0 | 10 | Editor routes |
| Enterprise Consistency | 8.0 | 10 | Single product walkthrough |
| Performance | 9.0 | 10 | ReactFlow CI benchmark |
| Accessibility | 6.5 | 10 | SR graph, focus rings |
| Maintainability | 8.5 | 10 | Legacy archive |
| Product Identity | 7.5 | 10 | Kill SaaS editor chrome |

**Weighted product maturity: 7.8 / 10**

---

## 13. Elevation Roadmap (Post-Analysis — Implementation Order)

### Batch E1 — Visual unity (2–3 days, no API)
1. Platform editor skin: `--fusion-bg-void` wrapper, kill `bg-background` in custom-types/flows/enrichers interiors
2. Fusion skeleton component for grids and panels
3. Unified empty-state component with CTA (open queue, run fusion, configure vault)

### Batch E2 — Graph excellence (3–5 days)
1. Entity glyph nodes on ReactFlow path (reuse entity-icons.tsx)
2. Layer toggles HUD: entities / tx / evidence / cross-case
3. In-graph search highlights + fly-to (palette action)

### Batch E3 — MIO depth (Phase 3)
1. Top-3 critical cards pinned briefing strip
2. Batch execute queue with dependency hints
3. Auto-refresh recommendations on workflow transition

### Batch E4 — Accessibility & polish
1. Focus visible on all fusion interactive chips
2. Graph aria-live region for alert propagation
3. Contextual error copy (API error → analyst action)

### Batch E5 — Legacy archive (after confirm)
1. Remove unused sidebar/root.layout if zero imports
2. Consolidate enterprise-ui into fusion panels or delete

---

## 14. Absolute Rule Compliance

| Gate | Status |
|------|--------|
| No API breaks | ✅ Analysis respects |
| No functionality removal | ✅ Archive only with confirm |
| No perf regression | ✅ GPU gates in CI |
| No RFC violation | ✅ |
| No new architecture | ✅ Additive batches only |

---

**Next step:** User approves elevation batch (E1→E5) → incremental implementation with validation pass after each batch.

**Report path:** `docs/audit/product-elevation-2026-07-11.md`

---

## 15. Cross-Agent Validation (2026-07-11)

Detailed route/component/data-flow maps confirmed by independent scan ([Map screens and flows](890dbe48-cfa9-48dd-af1e-911b08230c36)):

| Finding | Confirmed detail |
|---------|------------------|
| Shell adoption | 3 FusionShell + 11 FusionPlatformShell + 8 redirect/auth |
| `--fs-*` in TSX | **0** — CSS-only debt (~85 refs in 3 files) |
| Layout orphan | `sidebar`/`top-navbar`/`root.layout` — zero dashboard imports |
| Dual API surface | `:5173` JWT `:5001` vs demo `:8877` separate catalog — **parity risk** |
| Shared empty/error UX | **Missing** — inline copy only; no `FusionEmptyState` / error boundary |
| Graph loading UX | Minimal (blank div); no fusion skeleton on graph stage |

**Consolidated conclusion across validation + elevation + map agents:** Product is **production-credible on Tier A**; elevation priority = **E1 visual unity** + **shared polish components** + **demo/prod API parity documentation** — then E2 graph glyphs.
