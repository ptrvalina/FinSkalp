# Typography

## Stack

```css
--fusion-font-sans: 'Inter', 'Segoe UI', system-ui, sans-serif;
--fusion-font-mono: 'IBM Plex Mono', 'JetBrains Mono', ui-monospace, monospace;
```

Import via Google Fonts or system fallback — no webfont blocking in dev.

## Scale (Compact Operational)

| Token | Size | Line | Weight | Use |
|-------|------|------|--------|-----|
| `--fusion-text-2xs` | 9px | 12px | 500 | Strip labels, column headers |
| `--fusion-text-xs` | 10px | 14px | 400 | Secondary mono |
| `--fusion-text-sm` | 11px | 16px | 400 | Body operational |
| `--fusion-text-base` | 12px | 18px | 500 | Panel titles |
| `--fusion-text-md` | 13px | 20px | 600 | Zone headers |
| `--fusion-text-lg` | 14px | 20px | 600 | Mission values |

## Tracking

- Labels (uppercase): `0.14em` – `0.18em`
- Mono data: `0.02em`
- Body: `0.01em`

## Rules

1. **Values are mono** — case refs, addresses, timestamps, scores
2. **Labels are sans uppercase micro** — never sentence case in strips
3. **No font size > 14px** in operational surfaces (headlines forbidden)
4. Tabular nums: `font-variant-numeric: tabular-nums` on all numeric cells

## Bloomberg Discipline

Information strip pattern: label above value, never side-by-side in dense tables.

## Military Compact

Line height tight (1.2–1.4). Paragraphs rare — prefer single-line truncation with title tooltip.
