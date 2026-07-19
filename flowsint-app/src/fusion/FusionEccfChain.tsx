import { cn } from '@/lib/utils'

import { fusionCopy } from './fusion-copy'

const ECCF_ORDER = [
  'new',
  'scoring',
  'fusion',
  'graph',
  'hypotheses',
  'evidence',
  'review',
  'recommendation',
  'filed',
] as const

type Props = {
  workflowStatus?: string | null
  caseRef: string
  contentHash?: string | null
  className?: string
}

export function FusionEccfChain({ workflowStatus, caseRef, contentHash, className }: Props) {
  const status = (workflowStatus ?? 'new').toLowerCase()
  const activeIdx = Math.max(0, ECCF_ORDER.indexOf(status as (typeof ECCF_ORDER)[number]))

  return (
    <div className={cn('fusion-eccf-chain', className)} data-testid="fusion-eccf-chain">
      <p className="fusion-text-micro mb-2 text-[var(--fusion-text-tertiary)]">
        {fusionCopy.eccf.chainTitle} · {caseRef}
      </p>
      <ol className="fusion-eccf-chain__steps">
        {ECCF_ORDER.map((step, idx) => {
          const done = idx < activeIdx
          const active = idx === activeIdx
          const label = fusionCopy.eccf.steps[step] ?? step
          return (
            <li
              key={step}
              className={cn(
                'fusion-eccf-chain__step',
                done && 'fusion-eccf-chain__step--done',
                active && 'fusion-eccf-chain__step--active'
              )}
            >
              <span className="fusion-eccf-chain__dot" aria-hidden />
              <span className="fusion-eccf-chain__label">{label}</span>
            </li>
          )
        })}
      </ol>
      {contentHash ? (
        <p className="fusion-text-micro mt-2 text-[var(--fusion-text-tertiary)]">
          {fusionCopy.eccf.custodyHash}:{' '}
          <span className="fusion-mono text-[var(--fusion-text-secondary)]">{contentHash.slice(0, 16)}…</span>
        </p>
      ) : null}
    </div>
  )
}
