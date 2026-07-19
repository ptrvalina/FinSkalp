# Motion Language

## Principles

1. **Purpose-driven** — motion encodes state change, not delight
2. **60fps target** — transform and opacity only in hot paths
3. **Subtle** — max 400ms duration; most 200–300ms
4. **Respect reduced motion** — `prefers-reduced-motion: reduce` disables pulse/cascade

## Catalog

| Token | Duration | Easing | Use |
|-------|----------|--------|-----|
| `--fusion-motion-fast` | 150ms | ease-out | Hover borders |
| `--fusion-motion-base` | 250ms | ease | Panel slide |
| `--fusion-motion-slow` | 400ms | ease-in-out | Graph node enter |
| `--fusion-motion-pulse` | 1600ms | ease-in-out | Alert pulse (loop) |
| `--fusion-motion-cascade` | 200ms/hop | linear | Risk propagation |

## Animations

### `fusion-panel-slide`

Panel enters from dock edge: `translateX(±8px)` + opacity 0→1.

### `fusion-feed-enter`

New intelligence: `translateY(-4px)` + opacity 0→1, 300ms.

### `fusion-live-dot`

SSE connected: 2s opacity pulse on green indicator.

### `fusion-graph-node-in`

Staggered node appear (existing `complianceNodeIn`, aliased).

## Prohibited

- Bounce easing
- Parallax
- Full-screen transitions
- Loading spinners > 16px
- Confetti / shake

## Graph-Specific

Edge particles (existing) continue at low opacity. Cascade temporarily boosts traced edge opacity.
