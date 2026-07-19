# Color System — Operational Semantics

## Rule

Color **only** encodes operational meaning. No brand gradients, no decorative accents.

## Palette

| Token | Hex | Meaning |
|-------|-----|---------|
| `--fusion-ops-green` | `#3d9a62` | Clear / nominal / filed |
| `--fusion-ops-yellow` | `#c9a227` | Caution / pending review |
| `--fusion-ops-orange` | `#d97b2a` | Elevated risk / SLA warning |
| `--fusion-ops-red` | `#c94a4a` | Critical / breach / sanction hit |
| `--fusion-ops-blue` | `#4a7ec9` | Intelligence / active op / link |
| `--fusion-ops-gray` | `#5c6678` | Neutral / unknown / stale |

## Surface Tokens

```css
--fusion-bg-void: #0a0c10;
--fusion-bg-deck: #0f1218;
--fusion-bg-panel: #141820;
--fusion-bg-raised: #1a1f28;
--fusion-border: #252b36;
--fusion-border-strong: #323a48;
```

## Text Tokens

```css
--fusion-text-primary: #e8eaed;
--fusion-text-secondary: #9aa3b2;
--fusion-text-tertiary: #5c6678;
--fusion-text-mono: #c5cad4;
```

## Risk Mapping

| API risk_level | Color |
|----------------|-------|
| low | green |
| medium | yellow |
| high | orange |
| critical | red |

## Usage Constraints

- Max one accent color per panel zone
- Strip cells use color only on value, not label
- Graph nodes: border color by kind (future); alert overrides to red
- Never use purple/pink/teal

## Dark-Only

Fusion ships dark operational theme only. Light mode deferred indefinitely.
