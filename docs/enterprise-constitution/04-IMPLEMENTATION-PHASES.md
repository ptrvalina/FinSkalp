# Implementation Phases — Constitution v3

Derived from MASTER-PROMPT-005 success criteria. Each phase is additive; APIs remain stable.

---

## Phase 1 — Foundation (NOW)

**Goal:** Mission Control matches Constitution Chapter 3 — graph-dominant, no card dashboard.

| Deliverable | Success Criteria |
|-------------|------------------|
| `docs/enterprise-constitution/` | 5 canonical files; fusion docs marked superseded |
| Tokens v3 | `#0B1118` void, `#17222E` panel, semantic palette, no neon |
| Mission Control layout | Queue ~20%, Graph ~67%, MIO ~15%, bottom dock 5 tabs |
| Intelligence Ribbon | Mission strip + live activity ticker |
| Default route | `/` and `/dashboard` → `/dashboard/fusion` |
| Command palette | `Ctrl+K` with Find Case, Focus Entity, Open Timeline |
| Demo `:8877` | `fusion-deck.css` tokens + graph-center proportions |
| Typecheck | `npm run typecheck` green |

**Not in Phase 1:** GPU engine, collaboration cursors, executive mode, particle engine.

---

## Phase 2 — Graph Excellence

| Deliverable | Success Criteria |
|-------------|------------------|
| Graph persistence audit | Zero remount on dock resize / tab switch |
| Layer toggles | Entity/tx/evidence/cross-case HUD toggles |
| Performance baseline | 60fps @ 5k nodes on reference hardware |
| Alert animation | SSE → graph pulse without layout thrash |

---

## Phase 3 — Intelligence Officer Depth

| Deliverable | Success Criteria |
|-------------|------------------|
| MIO batch execute | Multi-card queue with dependency hints |
| Recommendation refresh | Auto-refresh on workflow transition |
| Officer briefing strip | Top-3 critical cards pinned above fold |

---

## Phase 4 — Docking & Workspace Memory

| Deliverable | Success Criteria |
|-------------|------------------|
| Float panels | Detach timeline/MIO to secondary monitor |
| Pin presets | Save/load named layouts |
| Cross-route memory | Queue width persists command ↔ investigation |

---

## Phase 5 — Legacy Sunset Complete

| Deliverable | Success Criteria |
|-------------|------------------|
| Remove `--fs-*` orphans | Single token source: `fusion/tokens.css` |
| Delete analyst-workspace shell | All compliance UX in fusion routes |
| Sidebar platform-only | Fusion never renders SaaS sidebar |

---

## Phase 6 — Scale & Performance

| Deliverable | Success Criteria |
|-------------|------------------|
| WebGL graph backend | 100k+ nodes with level-of-detail |
| Viewport culling | Off-screen nodes skip render |
| Benchmark suite | CI perf regression gate |

---

## Phase 7 — Collaboration & Executive (Deferred)

| Deliverable | Success Criteria |
|-------------|------------------|
| Live cursors | Multi-analyst presence on graph |
| Cinematic executive mode | Read-only presentation layout |
| Money flow particles | Animated edge flows for briefings |

---

## Phase 1 Gap Tracking

After Phase 1 ship, audit remaining gaps vs constitution (see coordinator summary).
