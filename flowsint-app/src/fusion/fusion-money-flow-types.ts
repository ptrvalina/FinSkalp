/** Money flow visual semantics from edge rel_type heuristics — no API (U5) */

export type MoneyFlowType =
  | 'layering'
  | 'peeling'
  | 'bridge'
  | 'mixer'
  | 'exchange'
  | 'sanction'
  | 'fiat'
  | 'crypto'
  | 'default'

export type MoneyFlowVisual = {
  type: MoneyFlowType
  color: string
  dash?: number[]
  particleSize: number
  speed: number
  label: string
}

const FLOW_VISUALS: Record<MoneyFlowType, Omit<MoneyFlowVisual, 'type'> & { canvasColor: string }> = {
  layering: {
    color: 'var(--fusion-ops-yellow)',
    canvasColor: '#D4A017',
    dash: [6, 4],
    particleSize: 2.5,
    speed: 0.35,
    label: 'Layering',
  },
  peeling: {
    color: 'var(--fusion-ops-cyan)',
    canvasColor: '#2EC4CF',
    dash: [2, 6],
    particleSize: 2,
    speed: 0.5,
    label: 'Peeling',
  },
  bridge: {
    color: 'var(--fusion-ops-blue)',
    canvasColor: '#4A8FD4',
    dash: [8, 2, 2, 2],
    particleSize: 3,
    speed: 0.4,
    label: 'Bridge',
  },
  mixer: {
    color: '#9B7FD4',
    canvasColor: '#9B7FD4',
    dash: [1, 3],
    particleSize: 2.2,
    speed: 0.65,
    label: 'Mixer',
  },
  exchange: {
    color: '#D4A017',
    canvasColor: '#D4A017',
    particleSize: 3.2,
    speed: 0.55,
    label: 'Exchange',
  },
  sanction: {
    color: 'var(--fusion-ops-red)',
    canvasColor: '#D64545',
    dash: [4, 4],
    particleSize: 3.5,
    speed: 0.25,
    label: 'Sanction',
  },
  fiat: {
    color: '#6B8E6B',
    canvasColor: '#6B8E6B',
    dash: [10, 5],
    particleSize: 2,
    speed: 0.3,
    label: 'Fiat',
  },
  crypto: {
    color: 'var(--fusion-ops-cyan)',
    canvasColor: '#2EC4CF',
    particleSize: 2.8,
    speed: 0.45,
    label: 'Crypto',
  },
  default: {
    color: 'var(--fusion-ops-cyan)',
    canvasColor: '#2EC4CF',
    particleSize: 2,
    speed: 0.4,
    label: 'Transfer',
  },
}

export function inferMoneyFlowType(relType?: string | null): MoneyFlowType {
  const r = (relType ?? '').toLowerCase()
  if (/sanction|ofac|blocked|blacklist/.test(r)) return 'sanction'
  if (/mixer|tumbler|coinjoin|privacy/.test(r)) return 'mixer'
  if (/exchange|cex|dex|swap/.test(r)) return 'exchange'
  if (/bridge|cross.?chain|hop/.test(r)) return 'bridge'
  if (/layer|structuring|smurf/.test(r)) return 'layering'
  if (/peel|chain.?hop|consolidat/.test(r)) return 'peeling'
  if (/fiat|bank|wire|swift|sepa|rub|usd|eur/.test(r)) return 'fiat'
  if (/crypto|on.?chain|tx|transfer|send|receive|wallet/.test(r)) return 'crypto'
  return 'default'
}

export function moneyFlowVisual(relType?: string | null): MoneyFlowVisual {
  const type = inferMoneyFlowType(relType)
  return { type, ...FLOW_VISUALS[type] }
}

export const MONEY_FLOW_TYPES: MoneyFlowType[] = [
  'layering',
  'peeling',
  'bridge',
  'mixer',
  'exchange',
  'sanction',
  'fiat',
  'crypto',
  'default',
]

export type MoneyFlowLayerToggles = Record<MoneyFlowType, boolean>

export const DEFAULT_MONEY_FLOW_LAYERS: MoneyFlowLayerToggles = Object.fromEntries(
  MONEY_FLOW_TYPES.map((t) => [t, true])
) as MoneyFlowLayerToggles
