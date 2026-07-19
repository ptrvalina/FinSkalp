export type WalletChain = 'tron' | 'eth' | 'btc' | 'bsc' | 'polygon'

/** Chain selection for Collect · Seed. */
export type ChainMode = WalletChain | 'auto' | 'all'

export const CHAIN_OPTIONS: Array<{ id: ChainMode; label: string; hint?: string }> = [
  { id: 'auto', label: 'Авто', hint: 'Определить по формату адреса' },
  { id: 'all', label: 'Все сети', hint: 'Проверка по всем сетям, где адрес валиден' },
  { id: 'tron', label: 'TRON' },
  { id: 'eth', label: 'ETH' },
  { id: 'bsc', label: 'BSC' },
  { id: 'polygon', label: 'Polygon' },
  { id: 'btc', label: 'BTC' },
]

export function inferWalletChain(address: string): WalletChain {
  const trimmed = address.trim()
  if (/^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(trimmed)) return 'tron'
  if (/^0x[a-fA-F0-9]{40}$/.test(trimmed)) return 'eth'
  if (/^([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})$/.test(trimmed)) return 'btc'
  return 'tron'
}

export function isLikelyWalletAddress(address: string): boolean {
  const trimmed = address.trim()
  if (trimmed.length < 26) return false
  return (
    /^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(trimmed) ||
    /^0x[a-fA-F0-9]{40}$/.test(trimmed) ||
    /^([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})$/.test(trimmed)
  )
}

export function buildWalletCaseRef(address: string): string {
  const slug = address.trim().slice(0, 8).toUpperCase().replace(/[^A-Z0-9]/g, '')
  const suffix = Date.now().toString(36).slice(-4).toUpperCase()
  return `WL-${slug || 'ADDR'}-${suffix}`
}

/** Strip `tron:T…` / `eth:0x…` prefixes for stable address comparison. */
export function normalizeWalletAddress(address: string): string {
  const trimmed = address.trim()
  const m = trimmed.match(/^(tron|eth|btc|bsc|polygon|sol):(.+)$/i)
  return (m ? m[2] : trimmed).toLowerCase()
}

/** Chains where this address format is valid. */
export function chainsForAddress(address: string): WalletChain[] {
  const trimmed = address.trim()
  if (/^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(trimmed)) return ['tron']
  if (/^0x[a-fA-F0-9]{40}$/.test(trimmed)) return ['eth', 'bsc', 'polygon']
  if (/^([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})$/.test(trimmed)) return ['btc']
  return ['tron']
}

/** Resolve concrete chains to scan for Collect / KYT. */
export function resolveChainsToScan(address: string, mode: ChainMode): WalletChain[] {
  const valid = chainsForAddress(address)
  if (mode === 'auto') return [valid[0] ?? 'tron']
  if (mode === 'all') return valid.length ? valid : ['tron', 'eth', 'btc']
  if (valid.includes(mode)) return [mode]
  // User forced a chain that doesn't match format — still try primary inference
  return [valid[0] ?? mode]
}

export function isChainMode(value: string): value is ChainMode {
  return CHAIN_OPTIONS.some((o) => o.id === value)
}
