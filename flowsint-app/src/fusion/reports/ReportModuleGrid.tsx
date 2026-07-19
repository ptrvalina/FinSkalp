import type { CSSProperties } from 'react'
import { Link } from '@tanstack/react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

import { complianceService } from '@/api/compliance-service'

import { FusionEmptyState } from '../FusionEmptyState'
import { FusionSkeleton } from '../FusionSkeleton'
import { fusionCopy } from '../fusion-copy'

import { isModuleReady, REPORT_MODULES } from './report-catalog'
import { ReportMoneyFlowChart } from './ReportCharts'
import type { ReportCaseBundle, ReportCategory, ReportModuleDef } from './report-types'

type Props = {
  caseRef: string
  bundle: ReportCaseBundle
  categoryFilter?: ReportCategory | 'all'
}

function riskScore(bundle: ReportCaseBundle): string {
  const fusion = bundle.fusion
  if (fusion?.illegal_flow_score != null) return String(fusion.illegal_flow_score)
  const pt = bundle.riskHistory.points.at(-1)
  if (pt) return String(pt.score)
  return '—'
}

function confidenceLabel(bundle: ReportCaseBundle): string {
  const raw =
    bundle.fusion?.confidence ??
    (bundle.fusion?.confidence_dimensions as Record<string, unknown> | undefined)
      ?.aggregate_risk_score
  if (raw == null) return '—'
  const n = Number(raw)
  if (Number.isFinite(n) && n <= 1) return `${Math.round(n * 100)}%`
  if (Number.isFinite(n)) return `${Math.round(n)}%`
  return String(raw)
}

function ModulePreview({ module, bundle }: { module: ReportModuleDef; bundle: ReportCaseBundle }) {
  const ready = isModuleReady(module, bundle.readiness)
  const nodes = bundle.graph?.nodes?.length ?? 0
  const edges = bundle.graph?.edges?.length ?? 0

  if (module.id === 'executive-brief' || module.id === 'executive-summary') {
    return (
      <div className="fusion-report-module-card__preview fusion-report-module-card__preview--brief">
        <div className="fusion-report-module-card__score fusion-tone-critical">{riskScore(bundle)}</div>
        <div className="fusion-text-micro text-[var(--fusion-text-tertiary)]">RISK SCORE</div>
        <div className="fusion-report-module-card__mini-stats">
          <span>{nodes} nodes</span>
          <span>{confidenceLabel(bundle)} conf</span>
        </div>
      </div>
    )
  }

  if (module.id === 'money-flow') {
    const bridges = (bundle.fusion?.bridges as unknown[] | undefined)?.length ?? 0
    return (
      <div className="fusion-report-module-card__preview fusion-report-module-card__preview--flow">
        <ReportMoneyFlowChart bundle={bundle} compact />
        <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
          {bridges} bridges · {edges} flows
        </span>
      </div>
    )
  }

  if (module.id === 'evidence-dossier') {
    return (
      <div className="fusion-report-module-card__preview">
        <div className="fusion-text-data">{bundle.evidence.count}</div>
        <div className="fusion-text-micro text-[var(--fusion-text-tertiary)]">EVIDENCE ITEMS</div>
      </div>
    )
  }

  if (module.id === 'timeline') {
    return (
      <div className="fusion-report-module-card__preview fusion-report-module-card__preview--timeline">
        {bundle.timeline.events.slice(0, 4).map((ev) => {
          const e = ev as { id: string; event_type: string }
          return <span key={e.id} className="fusion-report-timeline-dot" title={e.event_type} />
        })}
        <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
          {bundle.timeline.count} events
        </span>
      </div>
    )
  }

  if (module.category === 'entity' || module.id === 'graph-intelligence') {
    return (
      <div className="fusion-report-module-card__preview fusion-report-module-card__preview--graph">
        <div className="fusion-report-graph-orbit">
          <span className="fusion-report-graph-orbit__core" />
          {Array.from({ length: Math.min(6, nodes) }).map((_, i) => (
            <span key={i} className="fusion-report-graph-orbit__node" style={{ '--i': i } as CSSProperties} />
          ))}
        </div>
        <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">{nodes} entities</span>
      </div>
    )
  }

  return (
    <div className="fusion-report-module-card__preview">
      <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
        {ready ? fusionCopy.reports.ready : fusionCopy.reports.awaitingData}
      </span>
    </div>
  )
}

export function ReportModuleGrid({ caseRef, bundle, categoryFilter = 'all' }: Props) {
  const queryClient = useQueryClient()

  const fuseMutation = useMutation({
    mutationFn: () => complianceService.fuseCaseAsync(bundle.caseId!),
    onSuccess: () => {
      toast.success('Fusion queued — refresh in ~30s')
      void queryClient.invalidateQueries({ queryKey: ['compliance', 'case', bundle.caseId] })
    },
    onError: () => toast.error('Fusion failed'),
  })

  if (bundle.loading) return <FusionSkeleton variant="card" className="m-4" />

  const modules = REPORT_MODULES.filter(
    (m) => m.id !== 'export-center' && m.id !== 'pdf-preview' && m.id !== 'presentation-mode'
  ).filter((m) => categoryFilter === 'all' || m.category === categoryFilter)

  if (!bundle.caseId) {
    return (
      <FusionEmptyState
        className="m-6"
        title={fusionCopy.reports.noCaseId}
        description={fusionCopy.reports.noCasesDescription}
      />
    )
  }

  return (
    <div className="fusion-report-module-grid" data-testid="fusion-report-module-grid">
      <header className="fusion-report-module-grid__header">
        <h1 className="fusion-text-section">{fusionCopy.reports.moduleGridTitle}</h1>
        <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
          {fusionCopy.reports.moduleGridDescription}
        </p>
        <div className="fusion-report-living-metrics">
          <Metric label="Evidence" value={String(bundle.evidence.count)} />
          <Metric label="Graph" value={String(bundle.graph?.nodes?.length ?? 0)} />
          <Metric label="Timeline" value={String(bundle.timeline.count)} />
          <Metric label="Risk" value={riskScore(bundle)} tone="critical" />
          <Metric label="Reports" value={String(bundle.generatedReports.length)} />
        </div>
        {!bundle.readiness.fusion && bundle.caseId ? (
          <div className="fusion-report-module-grid__fuse-banner">
            <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
              Fusion not complete — reports may show draft state.
            </span>
            <button
              type="button"
              className="fusion-report-doc__btn"
              disabled={fuseMutation.isPending}
              onClick={() => fuseMutation.mutate()}
            >
              {fuseMutation.isPending ? 'Queuing…' : 'Run Fusion'}
            </button>
          </div>
        ) : null}
      </header>

      <div className="fusion-report-module-grid__cards">
        {modules.map((module) => {
          const ready = isModuleReady(module, bundle.readiness)
          return (
            <Link
              key={module.id}
              to="/dashboard/fusion/reports/$caseRef/$reportType"
              params={{ caseRef, reportType: module.id }}
              className={cn(
                'fusion-report-module-card',
                !ready && 'fusion-report-module-card--muted'
              )}
            >
              <div className="fusion-report-module-card__head">
                <span className="fusion-report-module-card__glyph" aria-hidden>
                  {module.glyph}
                </span>
                <div>
                  <h2 className="fusion-text-micro font-medium">{module.labelRu}</h2>
                  <p className="fusion-text-micro text-[var(--fusion-text-tertiary)] line-clamp-2">
                    {module.description}
                  </p>
                </div>
              </div>
              <ModulePreview module={module} bundle={bundle} />
              <footer className="fusion-report-module-card__foot">
                <span
                  className={cn(
                    'fusion-text-micro uppercase tracking-wider',
                    ready ? 'text-[var(--fusion-ops-green)]' : 'text-[var(--fusion-text-tertiary)]'
                  )}
                >
                  {ready ? fusionCopy.reports.ready : fusionCopy.reports.awaitingData}
                </span>
                <span className="fusion-text-micro text-[var(--fusion-ops-blue)]">
                  {fusionCopy.reports.openReport} →
                </span>
              </footer>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: 'critical'
}) {
  return (
    <div className="fusion-report-living-metrics__item">
      <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">{label}</span>
      <span
        className={cn(
          'fusion-mono fusion-text-data',
          tone === 'critical' && 'fusion-tone-critical'
        )}
      >
        {value}
      </span>
    </div>
  )
}
