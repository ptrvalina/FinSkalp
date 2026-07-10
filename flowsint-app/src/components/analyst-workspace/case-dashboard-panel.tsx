import { useQuery } from '@tanstack/react-query'

import { complianceService } from '@/api/compliance-service'
import {
  EnterpriseContextBar,
  EnterprisePanel,
  EnterpriseStatCard,
  RiskBadge,
  type RiskLevel,
} from '@/components/enterprise/enterprise-ui'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Activity, Briefcase, FileText, ShieldAlert } from 'lucide-react'

type Props = {
  caseRef: string
  investigationName: string
  workflow?: Record<string, unknown>
  counts?: { evidence?: number; timeline?: number; entities?: number }
  intelligence?: { rule_ru?: string; engines_count?: number; supported_chains?: string[] }
  recommendations?: Array<{ id: string; action_ru: string; explanation_ru: string }>
  onOpenRisk?: () => void
  riskLevel?: RiskLevel
}

function scoreToRisk(score: number): RiskLevel {
  if (score >= 75) return 'critical'
  if (score >= 55) return 'high'
  if (score >= 35) return 'medium'
  return 'low'
}

export function CaseDashboardPanel({
  caseRef,
  investigationName,
  workflow,
  counts,
  intelligence,
  recommendations,
  onOpenRisk,
  riskLevel = 'high',
}: Props) {
  const statsQuery = useQuery({
    queryKey: ['compliance', 'workflow-stats'],
    queryFn: () => complianceService.getWorkflowStats(),
    staleTime: 60_000,
  })

  const rdeQuery = useQuery({
    queryKey: ['compliance', 'rde-assess', caseRef],
    queryFn: () =>
      complianceService.assessRde({
        entityKey: caseRef,
        caseRef,
        signals: { workspace: true },
      }),
    enabled: Boolean(caseRef),
  })

  const derivedRisk = rdeQuery.data?.ok
    ? scoreToRisk(rdeQuery.data.composite_score)
    : riskLevel

  return (
    <div className="space-y-4">
      <EnterpriseContextBar
        caseId={caseRef}
        status={String(workflow?.workflow_status ?? 'active')}
        priority={String(workflow?.priority ?? 'medium')}
        owner={String(workflow?.assignee ?? 'Assigned analyst')}
        risk={derivedRisk}
        objectCount={String(counts?.entities ?? counts?.timeline ?? 0)}
        evidenceCount={String(counts?.evidence ?? 0)}
      />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <EnterpriseStatCard
          label="Доказательства"
          value={String(counts?.evidence ?? 0)}
          detail="Зарегистрировано в контексте дела"
          icon={<ShieldAlert className="h-5 w-5" />}
        />
        <EnterpriseStatCard
          label="События"
          value={String(counts?.timeline ?? 0)}
          detail="Записей в хронологии расследования"
          icon={<Activity className="h-5 w-5" />}
        />
        <EnterpriseStatCard
          label="В workflow"
          value={String(statsQuery.data?.pipeline?.in_progress ?? statsQuery.data?.total ?? '—')}
          detail="Активные дела в конвейере"
          icon={<Briefcase className="h-5 w-5" />}
          tone="accent"
        />
        <EnterpriseStatCard
          label="RDE score"
          value={rdeQuery.data?.ok ? String(Math.round(rdeQuery.data.composite_score)) : '—'}
          detail={
            rdeQuery.data?.ok
              ? `${rdeQuery.data.risk_level} · ${rdeQuery.data.recommendation_count} рекомендаций`
              : 'Оценка риска через RDE'
          }
          icon={<FileText className="h-5 w-5" />}
          tone={derivedRisk === 'critical' || derivedRisk === 'high' ? 'critical' : 'default'}
        />
      </div>

      <EnterprisePanel
        title="Investigation Briefing"
        description={`${investigationName} · ${caseRef}`}
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2 text-sm text-muted-foreground">
            {intelligence?.rule_ru ? <p>{intelligence.rule_ru}</p> : null}
            {intelligence?.supported_chains?.length ? (
              <p className="text-xs">Chains: {intelligence.supported_chains.join(', ')}</p>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">RFC-0010</Badge>
              {workflow?.workflow_status ? (
                <Badge variant="secondary">{String(workflow.workflow_status)}</Badge>
              ) : null}
              {intelligence?.engines_count != null ? (
                <Badge variant="outline">{intelligence.engines_count} engines</Badge>
              ) : null}
            </div>
          </div>
          <RiskBadge level={derivedRisk} onClick={onOpenRisk} />
        </div>

        {recommendations?.length ? (
          <div className="mt-4 space-y-2">
            <p className="text-xs font-medium text-foreground">Рекомендации workflow</p>
            {recommendations.slice(0, 4).map((rec) => (
              <div
                key={rec.id}
                className="rounded-sm border border-dashed border-[var(--fs-border-strong)] bg-[var(--fs-bg-secondary)] p-3 text-xs"
              >
                {rec.action_ru} — {rec.explanation_ru}
              </div>
            ))}
          </div>
        ) : null}

        {rdeQuery.isLoading ? <Skeleton className="mt-4 h-8 w-full" /> : null}
      </EnterprisePanel>
    </div>
  )
}
