import type { ReactNode } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  Binary,
  Briefcase,
  CircleAlert,
  FileSearch,
  Link2,
  ShieldCheck,
} from 'lucide-react'

import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Separator } from '@/components/ui/separator'

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

type EvidenceItem = {
  id: string
  type: string
  source: string
  checksum: string
  receivedAt: string
  verified: 'verified' | 'pending' | 'review'
}

type EntityItem = {
  title: string
  subtitle: string
  attributes: string[]
  sources: string[]
  confidence: number
  risk: RiskLevel
}

const RISK_META: Record<
  RiskLevel,
  { label: string; border: string; text: string; bg: string; pill: string }
> = {
  low: {
    label: 'Low',
    border: 'border-[var(--fs-risk-low)]/40',
    text: 'text-[var(--fs-risk-low)]',
    bg: 'bg-[color-mix(in_srgb,var(--fs-risk-low)_12%,transparent)]',
    pill: 'bg-[color-mix(in_srgb,var(--fs-risk-low)_18%,transparent)] text-[var(--fs-risk-low)]',
  },
  medium: {
    label: 'Medium',
    border: 'border-[var(--fs-risk-medium)]/40',
    text: 'text-[var(--fs-risk-medium)]',
    bg: 'bg-[color-mix(in_srgb,var(--fs-risk-medium)_12%,transparent)]',
    pill:
      'bg-[color-mix(in_srgb,var(--fs-risk-medium)_18%,transparent)] text-[var(--fs-risk-medium)]',
  },
  high: {
    label: 'High',
    border: 'border-[var(--fs-risk-high)]/40',
    text: 'text-[var(--fs-risk-high)]',
    bg: 'bg-[color-mix(in_srgb,var(--fs-risk-high)_12%,transparent)]',
    pill: 'bg-[color-mix(in_srgb,var(--fs-risk-high)_18%,transparent)] text-[var(--fs-risk-high)]',
  },
  critical: {
    label: 'Critical',
    border: 'border-[var(--fs-risk-critical)]/40',
    text: 'text-[var(--fs-risk-critical)]',
    bg: 'bg-[color-mix(in_srgb,var(--fs-risk-critical)_12%,transparent)]',
    pill:
      'bg-[color-mix(in_srgb,var(--fs-risk-critical)_18%,transparent)] text-[var(--fs-risk-critical)]',
  },
}

function checksumShort(value: string) {
  if (value.length <= 16) return value
  return `${value.slice(0, 8)}...${value.slice(-6)}`
}

export function EnterprisePageHero({
  eyebrow,
  title,
  description,
  actions,
  metrics,
}: {
  eyebrow?: string
  title: string
  description: string
  actions?: ReactNode
  metrics?: Array<{ label: string; value: string; tone?: 'default' | 'accent' | 'critical' }>
}) {
  return (
    <div className="rounded-lg border border-[var(--fs-border)] bg-[var(--fs-surface)]">
      <div className="flex flex-col gap-4 border-b border-[var(--fs-border)] px-6 py-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2">
          {eyebrow ? (
            <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--fs-text-secondary)]">
              {eyebrow}
            </p>
          ) : null}
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-[var(--fs-text-primary)]">
              {title}
            </h1>
            <p className="mt-1 max-w-3xl text-sm text-[var(--fs-text-secondary)]">{description}</p>
          </div>
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>
      {metrics?.length ? (
        <div className="grid gap-px bg-[var(--fs-border)] md:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <div
              key={`${metric.label}-${metric.value}`}
              className="bg-[var(--fs-bg-secondary)] px-6 py-4"
            >
              <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--fs-text-tertiary)]">
                {metric.label}
              </p>
              <p
                className={cn(
                  'mt-2 font-mono text-lg font-semibold',
                  metric.tone === 'accent' && 'text-[var(--fs-accent)]',
                  metric.tone === 'critical' && 'text-[var(--fs-risk-critical)]',
                  (!metric.tone || metric.tone === 'default') && 'text-[var(--fs-text-primary)]'
                )}
              >
                {metric.value}
              </p>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export function EnterprisePanel({
  title,
  description,
  actions,
  className,
  children,
}: {
  title: string
  description?: string
  actions?: ReactNode
  className?: string
  children: ReactNode
}) {
  return (
    <Card className={cn('border-[var(--fs-border)] bg-[var(--fs-surface)] shadow-none', className)}>
      <CardHeader className="border-b border-[var(--fs-border)] pb-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="text-sm font-semibold tracking-wide text-[var(--fs-text-primary)]">
              {title}
            </CardTitle>
            {description ? (
              <CardDescription className="mt-1 text-xs text-[var(--fs-text-secondary)]">
                {description}
              </CardDescription>
            ) : null}
          </div>
          {actions}
        </div>
      </CardHeader>
      <CardContent className="pt-4">{children}</CardContent>
    </Card>
  )
}

export function EnterpriseStatCard({
  label,
  value,
  detail,
  tone = 'default',
  icon,
}: {
  label: string
  value: string
  detail: string
  tone?: 'default' | 'accent' | 'critical'
  icon?: ReactNode
}) {
  return (
    <div className="rounded-md border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--fs-text-tertiary)]">
            {label}
          </p>
          <p
            className={cn(
              'mt-2 font-mono text-2xl font-semibold',
              tone === 'accent' && 'text-[var(--fs-accent)]',
              tone === 'critical' && 'text-[var(--fs-risk-critical)]',
              tone === 'default' && 'text-[var(--fs-text-primary)]'
            )}
          >
            {value}
          </p>
        </div>
        <div className="text-[var(--fs-text-secondary)]">{icon}</div>
      </div>
      <p className="mt-3 text-xs text-[var(--fs-text-secondary)]">{detail}</p>
    </div>
  )
}

export function EnterpriseContextBar({
  caseId,
  status,
  priority,
  owner,
  risk,
  objectCount,
  evidenceCount,
}: {
  caseId: string
  status: string
  priority: string
  owner: string
  risk: RiskLevel
  objectCount: string
  evidenceCount: string
}) {
  return (
    <div className="rounded-md border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="rounded-sm border border-[var(--fs-border-strong)] bg-transparent font-mono text-[11px] text-[var(--fs-text-primary)]">
          {caseId}
        </Badge>
        <Badge className="rounded-sm border border-[var(--fs-border)] bg-transparent text-[11px] text-[var(--fs-text-secondary)]">
          {status}
        </Badge>
        <Badge className="rounded-sm border border-[var(--fs-border)] bg-transparent text-[11px] text-[var(--fs-text-secondary)]">
          {priority}
        </Badge>
        <RiskBadge level={risk} />
        <span className="text-xs text-[var(--fs-text-secondary)]">Owner: {owner}</span>
        <span className="text-xs text-[var(--fs-text-secondary)]">{objectCount} entities</span>
        <span className="text-xs text-[var(--fs-text-secondary)]">{evidenceCount} evidence</span>
      </div>
    </div>
  )
}

export function RiskBadge({
  level,
  onClick,
  className,
}: {
  level: RiskLevel
  onClick?: () => void
  className?: string
}) {
  const meta = RISK_META[level]
  const body = (
    <span
      className={cn(
        'inline-flex items-center gap-2 rounded-sm border px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.14em]',
        meta.border,
        meta.bg,
        meta.text,
        className
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {meta.label}
    </span>
  )

  if (!onClick) {
    return body
  }

  return (
    <button type="button" onClick={onClick} className="text-left">
      {body}
    </button>
  )
}

export function ConfidenceIndicator({
  value,
  sources,
  freshness,
}: {
  value: number
  sources: string
  freshness: string
}) {
  const safeValue = Math.max(0, Math.min(100, value))

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.14em] text-[var(--fs-text-tertiary)]">
        <span>Confidence</span>
        <span className="font-mono text-[var(--fs-text-secondary)]">{safeValue}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[var(--fs-border)]">
        <div
          className="h-full rounded-full bg-[var(--fs-accent)]"
          style={{ width: `${safeValue}%` }}
        />
      </div>
      <div className="flex flex-wrap gap-3 text-xs text-[var(--fs-text-secondary)]">
        <span>{sources}</span>
        <span>{freshness}</span>
      </div>
    </div>
  )
}

export function EntityCard({ entity, compact = false }: { entity: EntityItem; compact?: boolean }) {
  return (
    <div className="rounded-md border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[var(--fs-text-primary)]">
            {entity.title}
          </p>
          <p className="mt-1 text-xs uppercase tracking-[0.14em] text-[var(--fs-text-tertiary)]">
            {entity.subtitle}
          </p>
        </div>
        <RiskBadge level={entity.risk} className="shrink-0" />
      </div>
      <div className="mt-3 space-y-2">
        {entity.attributes.slice(0, compact ? 2 : 3).map((attribute) => (
          <p key={attribute} className="text-xs text-[var(--fs-text-secondary)]">
            {attribute}
          </p>
        ))}
      </div>
      <div className="mt-3">
        <ConfidenceIndicator
          value={entity.confidence}
          sources={`${entity.sources.length} sources`}
          freshness="Fresh < 24h"
        />
      </div>
    </div>
  )
}

export function EvidenceRow({ item }: { item: EvidenceItem }) {
  return (
    <div className="grid gap-2 border-b border-[var(--fs-border)] py-3 text-sm md:grid-cols-[1.4fr_0.9fr_0.9fr_1fr_0.8fr] md:items-center">
      <div>
        <p className="font-mono text-xs text-[var(--fs-accent)]">{item.id}</p>
        <p className="mt-1 text-xs text-[var(--fs-text-secondary)]">{item.type}</p>
      </div>
      <p className="text-xs text-[var(--fs-text-secondary)]">{item.source}</p>
      <p className="text-xs text-[var(--fs-text-secondary)]">{item.receivedAt}</p>
      <p className="font-mono text-xs text-[var(--fs-text-secondary)]">
        {checksumShort(item.checksum)}
      </p>
      <Badge
        className={cn(
          'w-fit rounded-sm border bg-transparent text-[11px] uppercase tracking-[0.14em]',
          item.verified === 'verified' &&
            'border-[var(--fs-risk-low)]/40 text-[var(--fs-risk-low)]',
          item.verified === 'pending' &&
            'border-[var(--fs-risk-medium)]/40 text-[var(--fs-risk-medium)]',
          item.verified === 'review' &&
            'border-[var(--fs-risk-high)]/40 text-[var(--fs-risk-high)]'
        )}
      >
        {item.verified}
      </Badge>
    </div>
  )
}

export function ExplainabilityDrawer({
  open,
  onOpenChange,
  title,
  risk,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  risk: RiskLevel
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full border-l border-[var(--fs-border)] bg-[var(--fs-surface-raised)] text-[var(--fs-text-primary)] sm:max-w-2xl"
      >
        <SheetHeader>
          <div className="flex items-center gap-3">
            <RiskBadge level={risk} />
            <div>
              <SheetTitle className="text-left text-lg text-[var(--fs-text-primary)]">
                {title}
              </SheetTitle>
              <SheetDescription className="text-left text-sm text-[var(--fs-text-secondary)]">
                Evidence-first explainability for risk, rule triggers, and analyst review.
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="mt-6 space-y-5">
          <DrawerSection
            title="Data Used"
            icon={<FileSearch className="h-4 w-4" />}
            items={[
              'Entity graph snapshot for linked wallet cluster and counterparties',
              'Registry filings from sovereign gateway and licensed VASP lists',
              'Event stream from OSINT collectors and blockchain intelligence connectors',
            ]}
          />
          <DrawerSection
            title="Triggered Rules"
            icon={<Binary className="h-4 w-4" />}
            items={[
              'RFC-0013.47 IF 3+ high-risk counterparties AND rapid fan-out THEN escalate',
              'RFC-0016.09 IF registry mismatch persists > 24h THEN flag analyst confirmation',
              'RFC-0018.12 IF new evidence revises risk > 15 points THEN notify workspace',
            ]}
          />
          <DrawerSection
            title="Confidence Score"
            icon={<ShieldCheck className="h-4 w-4" />}
            items={[
              '4 independent sources corroborate the cluster attribution',
              'Latest confirmed source updated 19 minutes ago',
              'One heuristic remains analyst-confirmation only and reduces certainty',
            ]}
          />
          <DrawerSection
            title="Alternative Explanations"
            icon={<CircleAlert className="h-4 w-4" />}
            items={[
              'Shared service wallet behavior may inflate fan-out intensity',
              'Dormant address revival could represent treasury rotation rather than laundering',
            ]}
          />
          <div className="rounded-md border border-dashed border-[var(--fs-border-strong)] bg-[var(--fs-bg-secondary)] p-4 text-sm text-[var(--fs-text-secondary)]">
            <div className="flex items-center gap-2 font-medium text-[var(--fs-text-primary)]">
              <AlertTriangle className="h-4 w-4 text-[var(--fs-risk-medium)]" />
              Human in the loop
            </div>
            <p className="mt-2">
              This score is an investigatory hypothesis. Analyst confirmation is required before it
              is treated as a reporting fact.
            </p>
            <div className="mt-4 flex gap-2">
              <Button size="sm" className="rounded-sm">
                Confirm finding
              </Button>
              <Button size="sm" variant="outline" className="rounded-sm border-[var(--fs-border)]">
                Request review
              </Button>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

function DrawerSection({
  title,
  icon,
  items,
}: {
  title: string
  icon: ReactNode
  items: string[]
}) {
  return (
    <section className="space-y-3 rounded-md border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-[var(--fs-text-primary)]">
        {icon}
        {title}
      </div>
      <Separator className="bg-[var(--fs-border)]" />
      <div className="space-y-2">
        {items.map((item) => (
          <div
            key={item}
            className="flex items-start gap-2 text-sm text-[var(--fs-text-secondary)]"
          >
            <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--fs-accent)]" />
            <span>{item}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

export function DemoSummaryStrip() {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <EnterpriseStatCard
        label="Active Cases"
        value="24"
        detail="6 require analyst sign-off before filing."
        icon={<Briefcase className="h-5 w-5" />}
      />
      <EnterpriseStatCard
        label="Critical Alerts"
        value="07"
        detail="New cross-border fund movements detected in last hour."
        tone="critical"
        icon={<AlertTriangle className="h-5 w-5" />}
      />
      <EnterpriseStatCard
        label="Connectors"
        value="18/19"
        detail="Registry, blockchain, and OSINT sources are synchronized."
        tone="accent"
        icon={<Link2 className="h-5 w-5" />}
      />
      <EnterpriseStatCard
        label="Reports Ready"
        value="12"
        detail="Draft SAR and evidence bundles prepared for analyst review."
        icon={<FileSearch className="h-5 w-5" />}
      />
    </div>
  )
}

export const demoEvidence: EvidenceItem[] = [
  {
    id: 'EV-2026-0000001042',
    type: 'Registry extract',
    source: 'Sovereign gateway',
    checksum: '2cf7e8f7cb3140118b4a4cf09c71b11531a73982',
    receivedAt: '09 Jul 2026 13:12',
    verified: 'verified',
  },
  {
    id: 'EV-2026-0000001048',
    type: 'Wallet screening',
    source: 'Blockchain intelligence',
    checksum: '7f09e1bb4cf0ef0bc91d981c1e20f88bc11f92c1',
    receivedAt: '09 Jul 2026 13:18',
    verified: 'pending',
  },
  {
    id: 'EV-2026-0000001054',
    type: 'Analyst note',
    source: 'Investigation workspace',
    checksum: '9cc17d9d8212fb4f3c72b2c08d13951e2ef90d22',
    receivedAt: '09 Jul 2026 13:41',
    verified: 'review',
  },
]

export const demoEntities: EntityItem[] = [
  {
    title: 'TRON settlement cluster',
    subtitle: 'Wallet cluster',
    attributes: ['28 linked addresses', 'Exposure to 3 sanctioned services', 'Rapid fan-out pattern'],
    sources: ['KYT', 'OSINT', 'Registry'],
    confidence: 84,
    risk: 'high',
  },
  {
    title: 'Baltic OTC broker',
    subtitle: 'Counterparty',
    attributes: ['License mismatch in registry', 'Beneficial owner unresolved', 'Case-linked since 2026-07-06'],
    sources: ['Registry', 'Media'],
    confidence: 71,
    risk: 'medium',
  },
  {
    title: 'Case operator node',
    subtitle: 'Investigation entity',
    attributes: ['Human-confirmed identity', 'Attached to 12 evidence items', 'Recent report draft requested'],
    sources: ['Manual review', 'Internal'],
    confidence: 93,
    risk: 'low',
  },
]
