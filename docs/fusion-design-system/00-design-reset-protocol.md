# Design Reset Protocol — FinSkalp Fusion

## Mandate

All existing FinSkalp UI is **LEGACY**. This is not a redesign — it is a **reinvention** of the operator surface. Backend, API, database, and RFC contracts remain frozen. Only presentation, layout, motion, and information hierarchy change.

## What Dies

| Pattern | Why it dies |
|---------|-------------|
| SaaS sidebar + card dashboard | Signals consumer product, not fusion center |
| KPI widgets / stat cards | Decorative density without operational meaning |
| Modal dialogs | Breaks flow; blocks graph context |
| Chatbot AI panels | Undermines analyst authority; wrong mental model |
| AdminLTE / TailAdmin visual lineage | Generic admin skin; zero mission identity |
| Bootstrap grid dashboards | Low density; no spatial memory |

## What Lives

- `compliance-service.ts` — sole data plane
- `ComplianceGraphView` — graph engine (fusion chrome wraps it)
- `useComplianceEvents` — live SSE intelligence
- All existing routes — parallel access preserved

## Fusion Identity

**National FI Fusion Center** × **Bloomberg Terminal** × **NASA Mission Control** × **Chainalysis Reactor**

Expensive interfaces share traits:

1. **Persistent spatial canvas** — the graph never leaves; panels orbit it
2. **Semantic color only** — green/yellow/orange/red/blue/gray encode state, never decoration
3. **3× density** — every pixel carries intelligence; labels are micro, values are bold
4. **No decorative chrome** — borders are 1px operational dividers; shadows are absent or surgical
5. **Motion with purpose** — pulse = alert, cascade = propagation, fade = new intelligence

## Namespace

All new code lives under `flowsint-app/src/fusion/` with CSS tokens `--fusion-*`. Legacy `--fs-*` tokens remain until Phase 4 deletion.

## Non-Negotiables

- Graph is THE HEART — always mounted in investigation workspace
- No modals — slide, dock, float only
- MIO (Mission Intelligence Officer) = action cards, not chat
- Multi-window: dockable, resizable, pinnable, `localStorage` persistence
- `npm run typecheck` must pass at every phase boundary

## Sign-Off Criteria

Phase 0 (this delivery): parallel fusion namespace, docs, command center + investigation routes, graph HUD. Legacy routes untouched and reachable.
