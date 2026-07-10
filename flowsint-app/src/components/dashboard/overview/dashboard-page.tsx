import { queryKeys } from '@/api/query-keys'
import { useQuery } from '@tanstack/react-query'
import { investigationService } from '@/api/investigation-service'
import { InvestigationSkeleton } from '../investigation/investigation-skeleton'
import { Link } from '@tanstack/react-router'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DemoSummaryStrip,
  EnterprisePageHero,
  EnterprisePanel,
  RiskBadge,
} from '@/components/enterprise/enterprise-ui'
import type { Investigation } from '@/types/investigation'

export function DashboardPage() {
  const {
    data: investigations,
    isLoading
  } = useQuery<Investigation[]>({
    queryKey: queryKeys.investigations.dashboard,
    queryFn: investigationService.get
  })

  if (isLoading || !investigations) {
    return <InvestigationSkeleton />
  }

  const casesCount = investigations.length
  const activeCasesCount = investigations.filter((item) => item.status === 'active').length
  const recentInvestigations = investigations.slice(0, 6)

  return (
    <main className="flex-1 overflow-auto bg-[var(--fs-bg-primary)]">
      <div className="mx-auto max-w-7xl space-y-6 px-6 py-6 xl:px-8">
        <EnterprisePageHero
          eyebrow="command-center"
          title="Command Center"
          description="Enterprise case pipeline, explainable risk recommendations, and connector health for the current sovereign investigation workspace."
          actions={
            <>
              <Button asChild size="sm" className="rounded-sm">
                <Link to="/dashboard/compliance">Open compliance lifecycle</Link>
              </Button>
              <Button
                asChild
                size="sm"
                variant="outline"
                className="rounded-sm border-[var(--fs-border)]"
              >
                <Link to="/dashboard/flows">Flow Architect</Link>
              </Button>
            </>
          }
          metrics={[
            { label: 'Investigations', value: String(casesCount) },
            { label: 'Active', value: String(activeCasesCount), tone: 'accent' },
            { label: 'Queued alerts', value: '19' },
            { label: 'Critical filings', value: '03', tone: 'critical' },
          ]}
        />

        <DemoSummaryStrip />

        <div className="grid gap-6 xl:grid-cols-[1.45fr_0.9fr]">
          <EnterprisePanel
            title="Active Investigations"
            description="Context-preserving case queue with direct access to analyst workspace."
          >
            <div className="space-y-3">
              {recentInvestigations.map((investigation, index) => (
                <Link
                  key={investigation.id}
                  to="/dashboard/investigations/$investigationId"
                  params={{ investigationId: investigation.id }}
                  className="block rounded-md border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] p-4 transition-colors hover:border-[var(--fs-border-strong)] hover:bg-[var(--fs-surface-raised)]"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-[var(--fs-text-primary)]">
                        {investigation.name}
                      </p>
                      <p className="mt-1 font-mono text-xs text-[var(--fs-text-secondary)]">
                        CASE-{investigation.id.slice(0, 8).toUpperCase()}
                      </p>
                    </div>
                    <RiskBadge
                      level={index === 0 ? 'critical' : index % 3 === 0 ? 'high' : 'medium'}
                    />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-[var(--fs-text-secondary)]">
                    <Badge className="rounded-sm border border-[var(--fs-border)] bg-transparent text-[var(--fs-text-secondary)]">
                      {investigation.status}
                    </Badge>
                    <span>Owner: Analyst team</span>
                    <span>Updated: {new Date(investigation.last_updated_at).toLocaleDateString()}</span>
                  </div>
                </Link>
              ))}
            </div>
          </EnterprisePanel>

          <div className="space-y-6">
            <EnterprisePanel
              title="AI Recommendations"
              description="Every recommendation exposes data lineage before analyst confirmation."
            >
              <div className="space-y-3 text-sm">
                {[
                  'Escalate two linked wallets into the current filing packet.',
                  'Request human review for a registry mismatch on Baltic OTC broker.',
                  'Refresh graph snapshot after new OSINT evidence landed 11 minutes ago.',
                ].map((item, index) => (
                  <div
                    key={item}
                    className="rounded-md border border-dashed border-[var(--fs-border-strong)] bg-[var(--fs-bg-secondary)] p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-[var(--fs-text-primary)]">{item}</p>
                      <RiskBadge level={index === 0 ? 'high' : 'medium'} />
                    </div>
                    <p className="mt-2 text-xs text-[var(--fs-text-secondary)]">
                      Hypothesis only. Analyst confirmation required.
                    </p>
                  </div>
                ))}
              </div>
            </EnterprisePanel>

            <EnterprisePanel title="System Health" description="Connector freshness, telemetry, and filing readiness.">
              <div className="space-y-3">
                {[
                  ['Registry gateway', 'Healthy', '4 min freshness'],
                  ['Blockchain intelligence', 'Healthy', '2 min freshness'],
                  ['Reporting engine', 'Attention', 'Queue depth above baseline'],
                ].map(([name, state, meta]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between gap-3 border-b border-[var(--fs-border)] pb-3 last:border-0 last:pb-0"
                  >
                    <div>
                      <p className="text-sm text-[var(--fs-text-primary)]">{name}</p>
                      <p className="text-xs text-[var(--fs-text-secondary)]">{meta}</p>
                    </div>
                    <Badge
                      className="rounded-sm border border-[var(--fs-border)] bg-transparent text-[var(--fs-text-secondary)]"
                    >
                      {state}
                    </Badge>
                  </div>
                ))}
              </div>
            </EnterprisePanel>
          </div>
        </div>
      </div>
    </main>
  )
}
