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
    wallet: 'var(--fs-graph-wallet)',
    person: 'var(--fs-graph-person)',
    company: 'var(--fs-graph-company)',
    bank: 'var(--fs-graph-exchange)',
    document: 'var(--fs-graph-document)',
    evidence: 'var(--fs-graph-evidence)',
    investigation: 'var(--fs-graph-investigation)',
  }
  return map[kind] ?? 'var(--fs-text-secondary)'
}
