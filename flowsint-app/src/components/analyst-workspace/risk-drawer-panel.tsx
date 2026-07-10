import { useQuery } from '@tanstack/react-query'

import { complianceService } from '@/api/compliance-service'
import { RiskBadge, type RiskLevel } from '@/components/enterprise/enterprise-ui'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { AlertTriangle, Binary, ShieldCheck } from 'lucide-react'

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  caseRef: string
  entityKey?: string | null
  risk?: RiskLevel
}

function scoreToRisk(score: number): RiskLevel {
  if (score >= 75) return 'critical'
  if (score >= 55) return 'high'
  if (score >= 35) return 'medium'
  return 'low'
}

export function RiskDrawerPanel({
  open,
  onOpenChange,
  caseRef,
  entityKey,
  risk = 'high',
}: Props) {
  const key = entityKey ?? caseRef

  const assessQuery = useQuery({
    queryKey: ['compliance', 'rde-drawer', key, caseRef],
    queryFn: () =>
      complianceService.assessRde({
        entityKey: key,
        caseRef,
        signals: { drawer: true },
      }),
    enabled: open && Boolean(key),
  })

  const rulesQuery = useQuery({
    queryKey: ['compliance', 'rde-rules-eval', caseRef, key],
    queryFn: () =>
      complianceService.evaluateRdeRules({
        case_ref: caseRef,
        entity_key: key,
      }),
    enabled: open && Boolean(caseRef),
  })

  const prioritiesQuery = useQuery({
    queryKey: ['compliance', 'rde-priorities', caseRef],
    queryFn: () => complianceService.getRdePriorities(caseRef),
    enabled: open && Boolean(caseRef),
  })

  const derivedRisk = assessQuery.data?.ok
    ? scoreToRisk(assessQuery.data.composite_score)
    : risk

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full border-l border-[var(--fs-border)] bg-[var(--fs-surface-raised)] sm:max-w-2xl overflow-y-auto"
      >
        <SheetHeader>
          <div className="flex items-center gap-3">
            <RiskBadge level={derivedRisk} />
            <div>
              <SheetTitle className="text-left">Risk Drawer · {caseRef}</SheetTitle>
              <SheetDescription className="text-left">
                RDE assessment, triggered rules, and investigation priorities
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          {assessQuery.isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : assessQuery.data?.ok ? (
            <section className="rounded-md border border-[var(--fs-border)] p-4 space-y-2">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <ShieldCheck className="h-4 w-4" />
                RDE composite score
              </div>
              <p className="font-mono text-2xl">{assessQuery.data.composite_score.toFixed(1)}</p>
              <p className="text-sm text-muted-foreground">
                Level: {assessQuery.data.risk_level} · stages: {assessQuery.data.stages.join(' → ')}
              </p>
              <Badge variant="outline">
                {assessQuery.data.recommendation_count} recommendations
              </Badge>
            </section>
          ) : (
            <p className="text-sm text-muted-foreground">RDE assessment unavailable</p>
          )}

          {rulesQuery.data?.events?.length ? (
            <section className="rounded-md border border-[var(--fs-border)] p-4 space-y-2">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Binary className="h-4 w-4" />
                Triggered rules ({rulesQuery.data.event_count})
              </div>
              <ul className="space-y-2 text-sm text-muted-foreground">
                {rulesQuery.data.events.slice(0, 8).map((e, i) => (
                  <li key={`${e.rule_id}-${i}`}>
                    <Badge variant="secondary" className="mr-2 text-[10px]">
                      {e.severity}
                    </Badge>
                    {e.message_ru}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {prioritiesQuery.data?.priorities?.length ? (
            <section className="rounded-md border border-[var(--fs-border)] p-4 space-y-2">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <AlertTriangle className="h-4 w-4" />
                Priorities
              </div>
              <ul className="space-y-1 text-sm">
                {prioritiesQuery.data.priorities.slice(0, 6).map((p) => (
                  <li key={`${p.object_type}-${p.object_key}`} className="font-mono text-xs">
                    {p.object_key} · {p.priority_score} ({p.urgency})
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            Human-in-the-loop: scores are investigatory hypotheses, not legal conclusions.
          </div>

          <Button size="sm" variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
