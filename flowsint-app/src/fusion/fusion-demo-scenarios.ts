/** Map DEMO-* case refs to offline scenario ids. Production FSK-* refs never match. */

const DEMO_PREFIXES = ['DEMO-RU', 'DEMO-']

export function resolveDemoScenarioId(caseRef?: string | null): string | undefined {
  if (!caseRef) return undefined
  const upper = caseRef.toUpperCase()
  if (!DEMO_PREFIXES.some((p) => upper.startsWith(p))) return undefined
  if (upper.includes('OFFSHORE') || upper.includes('BFDB')) return 'p2p_rub_offshore'
  if (upper.includes('MIXER')) return 'mixer_layering'
  return 'p2p_rub_offshore'
}

export function isDemoCaseRef(caseRef?: string | null): boolean {
  return resolveDemoScenarioId(caseRef) != null
}
