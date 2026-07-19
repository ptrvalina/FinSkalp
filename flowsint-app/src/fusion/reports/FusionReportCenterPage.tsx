import { useState } from 'react'

import { Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'

import { complianceService } from '@/api/compliance-service'

import { FusionPlatformShell } from '../FusionPlatformShell'
import { FusionEmptyState } from '../FusionEmptyState'
import { FusionSkeleton } from '../FusionSkeleton'
import { fusionCopy } from '../fusion-copy'
import { loadLastCaseRef } from '../fusion-mission-data'

import { FusionReportCenterShell } from './FusionReportCenterShell'
import { ReportDocumentView } from './ReportDocumentView'
import { ReportModuleGrid } from './ReportModuleGrid'
import { fetchReports } from './report-api'
import type { ReportCategory, ReportModuleId } from './report-types'
import { useReportCaseBundle } from './useReportCaseBundle'

type Props = {
  caseRef?: string
  reportType?: ReportModuleId
}

export function FusionReportCenterPage({ caseRef, reportType }: Props) {
  const effectiveRef = caseRef ?? loadLastCaseRef()
  const [category, setCategory] = useState<ReportCategory | 'all'>('all')

  const casesQuery = useQuery({
    queryKey: ['compliance', 'cases'],
    queryFn: () => complianceService.listCases(),
  })

  const matchedCase = casesQuery.data?.find(
    (c) => c.case_ref === (caseRef ?? effectiveRef) || c.id === (caseRef ?? effectiveRef)
  )

  const reportsQuery = useQuery({
    queryKey: ['compliance', 'reports', effectiveRef],
    queryFn: () => fetchReports(effectiveRef ?? undefined),
    enabled: Boolean(effectiveRef) && !caseRef,
    retry: false,
  })

  const bundle = useReportCaseBundle(caseRef ?? effectiveRef ?? '')

  const activeView =
    reportType === 'export-center'
      ? 'export'
      : reportType === 'presentation-mode'
        ? 'presentation'
        : 'modules'

  if (caseRef && reportType) {
    return (
      <FusionPlatformShell
        title={fusionCopy.reports.centerTitle}
        subtitle={caseRef}
        activeSection="reports"
        caseRef={caseRef}
        workflowStatus={matchedCase?.workflow_status}
      >
        <FusionReportCenterShell
          caseRef={caseRef}
          activeView={activeView}
          activeCategory={category}
          onCategoryChange={setCategory}
        >
          <ReportDocumentView
            caseRef={caseRef}
            reportType={reportType}
            presentation={reportType === 'presentation-mode'}
          />
        </FusionReportCenterShell>
      </FusionPlatformShell>
    )
  }

  if (caseRef) {
    return (
      <FusionPlatformShell
        title={fusionCopy.reports.centerTitle}
        subtitle={caseRef}
        activeSection="reports"
        caseRef={caseRef}
        workflowStatus={matchedCase?.workflow_status}
      >
        <FusionReportCenterShell
          caseRef={caseRef}
          activeView="modules"
          activeCategory={category}
          onCategoryChange={setCategory}
        >
          {casesQuery.isLoading ? (
            <FusionSkeleton variant="row" className="p-4" />
          ) : (
            <ReportModuleGrid caseRef={caseRef} bundle={bundle} categoryFilter={category} />
          )}
        </FusionReportCenterShell>
      </FusionPlatformShell>
    )
  }

  return (
    <FusionPlatformShell
      title={fusionCopy.reports.centerTitle}
      subtitle={fusionCopy.reports.centerSubtitle}
      activeSection="reports"
    >
      <ReportHubBody
        cases={casesQuery.data ?? []}
        loading={casesQuery.isLoading}
        reports={reportsQuery.data ?? []}
        reportsLoading={reportsQuery.isLoading && Boolean(effectiveRef)}
      />
    </FusionPlatformShell>
  )
}

function ReportHubBody({
  cases,
  loading,
  reports,
  reportsLoading,
}: {
  cases: Array<{ id: string; case_ref?: string; workflow_status?: string; priority?: string }>
  loading: boolean
  reports: Array<{ case_ref?: string; case_id: string; typology_code?: string }>
  reportsLoading: boolean
}) {
  if (loading) return <FusionSkeleton variant="row" className="p-4" />

  return (
    <div className="fusion-report-hub p-4 space-y-6" data-testid="fusion-report-hub">
      <section>
        <h2 className="fusion-text-section mb-2">{fusionCopy.reports.selectCase}</h2>
        {cases.length === 0 ? (
          <FusionEmptyState
            title={fusionCopy.reports.noCasesTitle}
            description={fusionCopy.reports.noCasesDescription}
          />
        ) : (
          <ul className="fusion-report-hub__cases">
            {cases.slice(0, 24).map((c) => (
              <li key={c.id}>
                <Link
                  to="/dashboard/fusion/reports/$caseRef"
                  params={{ caseRef: c.case_ref ?? c.id }}
                  className="fusion-report-hub__case-link"
                >
                  <span className="fusion-mono fusion-text-micro text-[var(--fusion-ops-blue)]">
                    {c.case_ref ?? c.id}
                  </span>
                  <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
                    {c.workflow_status?.replace(/_/g, ' ') ?? '—'}
                  </span>
                  {c.priority ? (
                    <span className="fusion-text-micro fusion-tone-warning uppercase">{c.priority}</span>
                  ) : null}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="fusion-text-micro text-[var(--fusion-text-tertiary)] uppercase tracking-wider mb-2">
          {fusionCopy.reports.recentReports}
        </h2>
        {reportsLoading ? (
          <FusionSkeleton variant="row" />
        ) : reports.length === 0 ? (
          <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
            {fusionCopy.reports.emptyDescription}
          </p>
        ) : (
          <ul className="space-y-2">
            {reports.slice(0, 12).map((r) => (
              <li key={r.case_id + (r.typology_code ?? '')} className="fusion-text-micro">
                <Link
                  to="/dashboard/fusion/reports/$caseRef"
                  params={{ caseRef: r.case_ref ?? r.case_id }}
                  className="text-[var(--fusion-ops-blue)] fusion-mono"
                >
                  {r.case_ref ?? r.case_id}
                </Link>
                <span className="text-[var(--fusion-text-tertiary)] ml-2">
                  {r.typology_code ?? 'report'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

export function FusionReportDocumentLayout({ children }: { children: React.ReactNode }) {
  return <div className="fusion-report-document">{children}</div>
}
