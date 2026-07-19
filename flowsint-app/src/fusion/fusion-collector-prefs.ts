/** Manual Scalpel collector selection — persisted per analyst session. */

const GLOBAL_KEY = 'finskalp-manual-collectors-v2'
const LEGACY_KEY = 'finskalp-manual-collectors'

/** Canonical collector IDs used when merging stale localStorage prefs. */
export const COMBAT_COLLECTOR_IDS = [
  'onchain_explorer',
  'sanctions_watchlist',
  'username_social',
  'username_probe',
  'abuse_scam_registry',
  'darknet_index',
  'darknet_tor',
  'clearnet_intel',
  'vasp_registry',
  'court_enforcement',
  'reverse_whois_dns',
] as const

export function loadEnabledCollectors(): string[] {
  try {
    const raw = localStorage.getItem(GLOBAL_KEY) ?? localStorage.getItem(LEGACY_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return parsed.filter((x): x is string => typeof x === 'string')
  } catch {
    return []
  }
}

export function saveEnabledCollectors(ids: string[]): void {
  try {
    localStorage.setItem(GLOBAL_KEY, JSON.stringify(ids))
    localStorage.removeItem(LEGACY_KEY)
  } catch {
    /* ignore quota / private mode */
  }
}

export function toggleCollector(id: string, enabled: boolean, current: string[]): string[] {
  const set = new Set(current)
  if (enabled) set.add(id)
  else set.delete(id)
  const next = [...set]
  saveEnabledCollectors(next)
  return next
}

export function defaultCollectorsFromCatalog(
  collectors: Array<{ id: string; selectable?: boolean; default_checked?: boolean }>
): string[] {
  return collectors
    .filter((c) => c.selectable !== false && c.default_checked !== false)
    .map((c) => c.id)
}

/**
 * Merge stored prefs with catalog defaults so newly added collectors
 * appear without forcing analysts to clear localStorage.
 */
export function mergeCollectorsWithCatalog(
  enabled: string[],
  catalog: Array<{ id: string; selectable?: boolean; default_checked?: boolean }>
): string[] {
  const defaults = defaultCollectorsFromCatalog(catalog)
  if (!enabled.length) return defaults.length ? defaults : [...COMBAT_COLLECTOR_IDS]
  const known = new Set(catalog.map((c) => c.id))
  const kept = enabled.filter(
    (id) => known.has(id) || (COMBAT_COLLECTOR_IDS as readonly string[]).includes(id)
  )
  if (defaults.length && kept.length < Math.max(4, Math.floor(defaults.length / 2))) {
    return [...new Set([...kept, ...defaults])]
  }
  const missingDefaults = defaults.filter((id) => !kept.includes(id))
  if (missingDefaults.length && kept.length > 0) {
    const coverage =
      kept.filter((id) => defaults.includes(id)).length / Math.max(defaults.length, 1)
    if (coverage >= 0.5) {
      return [...new Set([...kept, ...missingDefaults])]
    }
  }
  return kept.length ? kept : defaults
}
