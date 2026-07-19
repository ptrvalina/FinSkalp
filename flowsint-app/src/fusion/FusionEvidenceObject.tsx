import { cn } from '@/lib/utils'

type EvidencePayload = {
  trust_score?: number
  confidence?: number
  provenance?: string[]
  source_url?: string
  chain?: string
}

type Props = {
  id: string
  sourceType: string
  contentHash: string
  status?: string
  payload?: Record<string, unknown>
  linkedEntityCount?: number
  active?: boolean
  draggable?: boolean
  onClick?: () => void
  onDragStart?: (e: React.DragEvent) => void
  className?: string
}

function trustLabel(payload?: Record<string, unknown>): string {
  const p = payload as EvidencePayload
  const raw = p.trust_score ?? p.confidence
  if (typeof raw === 'number' && !Number.isNaN(raw)) {
    const pct = raw <= 1 ? Math.round(raw * 100) : Math.round(raw)
    return `${pct}%`
  }
  return '—'
}

function provenanceChain(payload?: Record<string, unknown>): string[] {
  const p = payload as EvidencePayload
  if (Array.isArray(p.provenance) && p.provenance.length) return p.provenance.slice(0, 4)
  const chain: string[] = []
  if (p.source_url) chain.push(String(p.source_url).slice(0, 40))
  if (p.chain) chain.push(String(p.chain))
  return chain
}

export function FusionEvidenceObject({
  sourceType,
  contentHash,
  status,
  payload,
  linkedEntityCount = 0,
  active,
  draggable,
  onClick,
  onDragStart,
  className,
}: Props) {
  const prov = provenanceChain(payload)

  return (
    <article
      className={cn(
        'fusion-evidence-object fusion-surface-deck p-2',
        active && 'ring-1 ring-[var(--fusion-ops-blue)]/50',
        draggable && 'cursor-grab active:cursor-grabbing',
        onClick && 'cursor-pointer hover:bg-[var(--fusion-bg-deck)]',
        className
      )}
      draggable={draggable}
      onDragStart={onDragStart}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onClick()
              }
            }
          : undefined
      }
      data-testid="fusion-evidence-object"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="fusion-text-micro uppercase text-[var(--fusion-ops-cyan)]">
          {sourceType}
        </span>
        {status ? (
          <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">{status}</span>
        ) : null}
      </div>
      <p className="mt-1 fusion-mono fusion-text-data fusion-truncate" title={contentHash}>
        {contentHash}
      </p>
      <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 fusion-text-micro">
        <span>
          <span className="text-[var(--fusion-text-tertiary)]">TRUST </span>
          {trustLabel(payload)}
        </span>
        <span>
          <span className="text-[var(--fusion-text-tertiary)]">LINKS </span>
          {linkedEntityCount}
        </span>
      </div>
      {prov.length > 0 ? (
        <ul className="mt-1 space-y-0.5">
          {prov.map((step, i) => (
            <li key={i} className="fusion-text-micro fusion-truncate text-[var(--fusion-text-tertiary)]">
              ↳ {step}
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  )
}
