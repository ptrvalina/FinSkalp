import { cn } from '@/lib/utils'

export const FUSION_STR_STEPS = [
  { id: 'new_str', label: 'Новый STR' },
  { id: 'scoring', label: 'Автоматический скоринг' },
  { id: 'fusion', label: 'OSINT Fusion' },
  { id: 'graph', label: 'Граф связей' },
  { id: 'hypothesis', label: 'Гипотезы' },
  { id: 'evidence', label: 'Подтверждение доказательствами' },
  { id: 'risk', label: 'Оценка риска' },
  { id: 'recommendation', label: 'Рекомендация' },
  { id: 'sar', label: 'SAR / Forensic Report' },
] as const

const WORKFLOW_TO_STEP: Record<string, number> = {
  new: 0,
  triage: 1,
  investigating: 3,
  pending_filing: 7,
  filed: 8,
  archived: 8,
}

type StepStatus = 'pending' | 'running' | 'done'

function resolveActiveIndex(workflowStatus?: string | null, fusionDone?: boolean): number {
  if (!workflowStatus) return 0
  const base = WORKFLOW_TO_STEP[workflowStatus] ?? 0
  if (workflowStatus === 'investigating' && fusionDone) return 4
  if (workflowStatus === 'investigating') return 3
  return base
}

export function FusionStrPipeline({
  workflowStatus,
  fusionDone = false,
  className,
}: {
  workflowStatus?: string | null
  fusionDone?: boolean
  className?: string
}) {
  const activeIndex = resolveActiveIndex(workflowStatus, fusionDone)

  return (
    <div
      className={cn('fusion-str-pipeline', className)}
      data-testid="fusion-str-pipeline"
      aria-label="STR investigation pipeline"
    >
      <ol className="fusion-str-pipeline__track">
        {FUSION_STR_STEPS.map((step, index) => {
          const status: StepStatus =
            index < activeIndex ? 'done' : index === activeIndex ? 'running' : 'pending'
          return (
            <li key={step.id} className="fusion-str-pipeline__step">
              <span
                className={cn(
                  'fusion-str-pipeline__pill',
                  status === 'done' && 'fusion-str-pipeline__pill--done',
                  status === 'running' && 'fusion-str-pipeline__pill--running',
                  status === 'pending' && 'fusion-str-pipeline__pill--pending'
                )}
              >
                <span
                  className={cn(
                    'fusion-str-pipeline__dot',
                    status === 'done' && 'fusion-str-pipeline__dot--done',
                    status === 'running' && 'fusion-str-pipeline__dot--running',
                    status === 'pending' && 'fusion-str-pipeline__dot--pending'
                  )}
                />
                {step.label}
              </span>
              {index < FUSION_STR_STEPS.length - 1 ? (
                <span className="fusion-str-pipeline__arrow" aria-hidden>
                  →
                </span>
              ) : null}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
