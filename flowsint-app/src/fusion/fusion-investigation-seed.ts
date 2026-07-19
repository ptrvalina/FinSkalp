import { inferWalletChain, isLikelyWalletAddress } from './fusion-wallet-utils'

export type SeedType =
  | 'wallet'
  | 'person'
  | 'organization'
  | 'username'
  | 'document'
  | 'transaction'
  | 'group'

export type InvestigationSeedItem = {
  type: SeedType
  value: string
  chain?: string
  /** Multi-chain combat scan list (Авто / Все сети) */
  chains?: string[]
  chainMode?: string
}

export type InvestigationSeed = {
  items: InvestigationSeedItem[]
}

const SEED_LINE =
  /^\s*(wallet|person|organization|org|username|user|document|doc|transaction|tx|group)\s*[:=]\s*(.+)\s*$/i

export function parseSeedPool(text: string): InvestigationSeedItem[] {
  const items: InvestigationSeedItem[] = []
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    const match = line.match(SEED_LINE)
    if (match) {
      const kind = normalizeSeedType(match[1]!)
      items.push({ type: kind, value: match[2]!.trim() })
      continue
    }
    if (isLikelyWalletAddress(line)) {
      items.push({ type: 'wallet', value: line, chain: inferWalletChain(line) })
      continue
    }
    if (line.startsWith('@')) {
      items.push({ type: 'username', value: line.replace(/^@/, '') })
      continue
    }
    if (looksLikeOrganization(line)) {
      items.push({ type: 'organization', value: line })
      continue
    }
    if (line.includes(' ')) {
      items.push({ type: 'person', value: line })
    } else {
      items.push({ type: 'organization', value: line })
    }
  }
  return items
}

const ORG_PREFIXES = ['ооо', 'оао', 'ао', 'пао', 'зао', 'нко', 'ип', 'llc', 'ltd', 'inc', 'corp', 'gmbh', 'plc']

function looksLikeOrganization(line: string): boolean {
  const t = line.trim().toLocaleLowerCase('ru-RU')
  return ORG_PREFIXES.some((p) => t === p || t.startsWith(`${p} `) || t.startsWith(`${p}.`) || t.startsWith(`${p}«`))
}

function normalizeSeedType(raw: string): SeedType {
  const k = raw.toLowerCase()
  if (k === 'org') return 'organization'
  if (k === 'user') return 'username'
  if (k === 'doc') return 'document'
  if (k === 'tx') return 'transaction'
  return k as SeedType
}

/** RU → LAT for Maigret (ASCII-only handles). */
const CYR_TO_LAT: Record<string, string> = {
  а: 'a',
  б: 'b',
  в: 'v',
  г: 'g',
  д: 'd',
  е: 'e',
  ё: 'e',
  ж: 'zh',
  з: 'z',
  и: 'i',
  й: 'y',
  к: 'k',
  л: 'l',
  м: 'm',
  н: 'n',
  о: 'o',
  п: 'p',
  р: 'r',
  с: 's',
  т: 't',
  у: 'u',
  ф: 'f',
  х: 'kh',
  ц: 'ts',
  ч: 'ch',
  ш: 'sh',
  щ: 'shch',
  ъ: '',
  ы: 'y',
  ь: '',
  э: 'e',
  ю: 'yu',
  я: 'ya',
}

export function transliterateCyrillic(value: string): string {
  return [...value.toLowerCase()].map((ch) => CYR_TO_LAT[ch] ?? ch).join('')
}

/**
 * ФИО → Latin Maigret usernames.
 * Spaces are split (never sent to Maigret as-is).
 * RU order: Фамилия Имя [Отчество].
 */
export function personToUsernames(fullName: string): string[] {
  const parts = fullName
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((p) => transliterateCyrillic(p).replace(/[^a-z0-9._-]/gi, ''))
    .filter((p) => p.length >= 2)
  if (!parts.length) return []

  const out = new Set<string>()
  const add = (t: string) => {
    const clean = t.replace(/^[._-]+|[._-]+$/g, '')
    if (clean.length >= 2) out.add(clean)
  }

  if (parts.length === 1) {
    add(parts[0]!)
    return [...out].slice(0, 6)
  }

  const surname = parts[0]!
  const given = parts[1]!
  add(surname)
  add(`${surname}_${given}`)
  add(`${given}_${surname}`)
  add(`${given}${surname}`)
  add(`${surname}${given}`)
  add(`${given[0]}${surname}`)
  add(`${surname}${given[0]}`)
  return [...out].slice(0, 6)
}

export function seedUsernames(items: InvestigationSeedItem[]): string[] {
  const out = new Set<string>()
  // Explicit @handles first — they are highest-signal for Maigret
  for (const item of items) {
    if (item.type === 'username') out.add(item.value.replace(/^@/, ''))
  }
  for (const item of items) {
    if (item.type === 'person') personToUsernames(item.value).forEach((u) => out.add(u))
  }
  return [...out].slice(0, 8)
}

export function primaryWallet(items: InvestigationSeedItem[]): InvestigationSeedItem | null {
  return items.find((i) => i.type === 'wallet') ?? null
}

export function buildCaseRefFromSeed(items: InvestigationSeedItem[]): string {
  const suffix = `${Date.now().toString(36).slice(-4)}${Math.random().toString(36).slice(2, 5)}`.toUpperCase()
  const wallet = primaryWallet(items)
  if (wallet) {
    const slug = wallet.value.slice(0, 8).toUpperCase().replace(/[^A-Z0-9]/g, '')
    return `WL-${slug || 'ADDR'}-${suffix}`
  }
  const person = items.find((i) => i.type === 'person')
  if (person) {
    const slug = person.value.split(/\s+/).pop()?.slice(0, 10).toUpperCase().replace(/[^A-ZА-Я0-9]/gi, '') ?? 'PERSON'
    return `PR-${slug}-${suffix}`
  }
  const org = items.find((i) => i.type === 'organization')
  if (org) {
    const slug = org.value.slice(0, 10).toUpperCase().replace(/[^A-ZА-Я0-9]/gi, '') ?? 'ORG'
    return `ORG-${slug}-${suffix}`
  }
  return `INV-${suffix}`
}

export function scalpelTargetAddress(items: InvestigationSeedItem[]): string {
  const wallet = primaryWallet(items)
  if (wallet) return wallet.value
  const person = items.find((i) => i.type === 'person')
  if (person) return `person:${person.value.slice(0, 48)}`
  const org = items.find((i) => i.type === 'organization')
  if (org) return `org:${org.value.slice(0, 48)}`
  const user = items.find((i) => i.type === 'username')
  if (user) return `user:${user.value.slice(0, 48)}`
  return `seed:${items[0]?.value.slice(0, 48) ?? 'unknown'}`
}

export function resolveChain(items: InvestigationSeedItem[]): string {
  const wallet = primaryWallet(items)
  if (wallet?.chain) return wallet.chain
  if (wallet) return inferWalletChain(wallet.value)
  return 'tron'
}

/** Collectors appropriate for the seed mix (wallet / person / org). */
export function defaultCollectorsForSeed(items: InvestigationSeedItem[]): string[] {
  const hasWallet = Boolean(primaryWallet(items))
  const hasPerson = items.some((i) => i.type === 'person' || i.type === 'username')
  const hasOrg = items.some((i) => i.type === 'organization')

  // Core OSINT collectors (sanctions / clearnet / darknet / court / DNS)
  const coreOsint = [
    'sanctions_watchlist',
    'clearnet_intel',
    'darknet_index',
    'darknet_tor',
    'court_enforcement',
    'reverse_whois_dns',
    'vasp_registry',
  ]

  const ids: string[] = [...coreOsint]

  if (hasWallet) {
    ids.push('onchain_explorer', 'abuse_scam_registry')
  }
  if (hasPerson) {
    ids.push('username_social', 'username_probe')
  }
  if (hasOrg) {
    // org already covered by core; keep explicit for clarity
    ids.push('vasp_registry')
  }
  if (!hasWallet && !hasPerson && !hasOrg) {
    ids.push('username_social', 'username_probe')
  }

  return [...new Set(ids)]
}

export function filterCollectorsForSeed(
  collectorIds: string[],
  items: InvestigationSeedItem[]
): string[] {
  const hasWallet = Boolean(primaryWallet(items))
  return collectorIds.filter((id) => {
    if (!hasWallet && (id === 'onchain_explorer' || id === 'abuse_scam_registry')) return false
    return true
  })
}

export function workflowSeedFromItems(items: InvestigationSeedItem[]): {
  seed_type: string
  seed_value: string
  chain: string
} {
  const wallet = primaryWallet(items)
  if (wallet) {
    return { seed_type: 'wallet', seed_value: wallet.value, chain: resolveChain(items) }
  }
  const person = items.find((i) => i.type === 'person')
  if (person) return { seed_type: 'person', seed_value: person.value, chain: resolveChain(items) }
  const org = items.find((i) => i.type === 'organization')
  if (org) return { seed_type: 'organization', seed_value: org.value, chain: resolveChain(items) }
  return { seed_type: 'document', seed_value: items[0]?.value ?? 'unknown', chain: 'tron' }
}
