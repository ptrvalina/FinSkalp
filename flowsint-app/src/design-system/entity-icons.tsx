/** RFC-0008 Ch.7 — unified entity iconography (Lucide) */

import {
  Building2,
  FileText,
  Fingerprint,
  Globe,
  Landmark,
  Scale,
  Smartphone,
  User,
  Wallet,
  type LucideIcon,
} from 'lucide-react'

export type EntityIconKind =
  | 'person'
  | 'company'
  | 'bank'
  | 'wallet'
  | 'document'
  | 'evidence'
  | 'report'
  | 'domain'
  | 'device'
  | 'investigation'

const ICON_MAP: Record<EntityIconKind, LucideIcon> = {
  person: User,
  company: Building2,
  bank: Landmark,
  wallet: Wallet,
  document: FileText,
  evidence: Fingerprint,
  report: FileText,
  domain: Globe,
  device: Smartphone,
  investigation: Scale,
}

const LABEL_RU: Record<EntityIconKind, string> = {
  person: 'Физическое лицо',
  company: 'Компания',
  bank: 'Банк',
  wallet: 'Кошелёк',
  document: 'Документ',
  evidence: 'Доказательство',
  report: 'Отчёт',
  domain: 'Домен',
  device: 'Устройство',
  investigation: 'Расследование',
}

type Props = {
  kind: EntityIconKind
  className?: string
  size?: number
}

export function EntityIcon({ kind, className = 'shrink-0', size = 16 }: Props) {
  const Icon = ICON_MAP[kind]
  return <Icon className={className} size={size} aria-label={LABEL_RU[kind]} />
}

export function entityGraphColorVar(kind: EntityIconKind): string {
  const map: Partial<Record<EntityIconKind, string>> = {
    wallet: 'var(--fusion-graph-wallet)',
    person: 'var(--fusion-graph-person)',
    company: 'var(--fusion-graph-company)',
    bank: 'var(--fusion-graph-exchange)',
    document: 'var(--fusion-graph-document)',
    evidence: 'var(--fusion-graph-evidence)',
    investigation: 'var(--fusion-graph-investigation)',
  }
  return map[kind] ?? 'var(--fusion-text-secondary)'
}

/** Map API graph node kind → icon kind for ReactFlow glyph nodes. */
export function resolveEntityIconKind(kind: string): EntityIconKind {
  const k = kind.toLowerCase()
  if (k.includes('wallet') || k.includes('address')) return 'wallet'
  if (k.includes('person')) return 'person'
  if (k.includes('company') || k.includes('org')) return 'company'
  if (k.includes('bank') || k.includes('exchange')) return 'bank'
  if (k.includes('evidence') || k.includes('osint')) return 'evidence'
  if (k.includes('document') || k.includes('report')) return 'document'
  if (k.includes('domain')) return 'domain'
  if (k.includes('device')) return 'device'
  if (k.includes('investigation') || k.includes('case')) return 'investigation'
  return 'company'
}
