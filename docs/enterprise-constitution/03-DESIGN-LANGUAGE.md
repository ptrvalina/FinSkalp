# Design Language — Constitution v3

## Visual Tone

Operational intelligence terminal — **dense, cold, precise**. Reference mood: Palantir Gotham / Bloomberg Terminal — without copying specific UI chrome.

Original FinSkalp identity: STR/crypto compliance, CIS regulatory context, Russian analyst copy.

---

## Color System

```css
--fusion-bg-void: #0B1118;
--fusion-bg-deck: #111A24;
--fusion-bg-panel: #17222E;
--fusion-bg-interactive: #1E2B39;

--fusion-text-primary: rgba(255, 255, 255, 0.92);
--fusion-text-secondary: rgba(255, 255, 255, 0.68);
--fusion-text-tertiary: rgba(255, 255, 255, 0.45);

--fusion-ops-green: #3BA86B;    /* verified */
--fusion-ops-yellow: #D4A017;   /* attention / amber */
--fusion-ops-red: #D64545;      /* risk */
--fusion-ops-purple: #9B7FD4;   /* intelligence */
--fusion-ops-cyan: #2EC4CF;     /* blockchain */
--fusion-ops-blue: #4A8FD4;     /* system */
```

**Forbidden:** neon gradients, glassmorphism hero cards, decorative purple/pink accents unrelated to semantics, light mode in fusion shell.

---

## Typography

| Role | Size | Font |
|------|------|------|
| Micro label | 9–10px uppercase, 0.14–0.18em tracking | Inter 500 |
| Data row | 11–12px | Inter / Plex Mono |
| Panel title | 12–13px uppercase | Inter 600 |
| Mono values | 12px tabular-nums | IBM Plex Mono |

---

## Spacing & Grid

- Base unit: 4px (`--fusion-space-1`)
- Panel header: 32px (`--fusion-panel-header`)
- Row height: 28px (`--fusion-row-height`)
- Rail: 48px (`--fusion-rail-width`)
- Mission strip: 56px (`--fusion-strip-height`)

---

## Motion

| Token | Duration | Use |
|-------|----------|-----|
| `--fusion-motion-fast` | 150ms | Hover, tab switch |
| `--fusion-motion-base` | 250ms | Panel pin, dock expand |
| `--fusion-motion-slow` | 400ms | Feed entry (subtle) |

No bounce, no parallax, no page transitions. `@media (prefers-reduced-motion: reduce)` disables animations.

---

## Panel Chrome

- 1px borders `--fusion-border` (#2A3847 approx)
- Radius: 2px max (`--fusion-radius-sm`)
- Pin state: blue inset ring — not drop shadow
- Zone labels: uppercase micro, semantic color on label only

---

## Quality Gate Checklist

- [ ] Zero gradient backgrounds in fusion CSS
- [ ] Semantic color max one accent per panel zone
- [ ] All fusion text meets 68%+ secondary contrast on panel bg
- [ ] Graph stage is full-bleed (no card padding)
- [ ] MIO panel contains zero chat input elements
