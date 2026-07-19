import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Download, ExternalLink, FileText } from 'lucide-react'
import { toast } from 'sonner'

import { cn } from '@/lib/utils'

import { complianceService } from '@/api/compliance-service'

import { fusionCopy } from '../fusion-copy'
import { FusionEmptyState } from '../FusionEmptyState'
import { FusionInlineError } from '../FusionInlineError'
import { FusionSkeleton } from '../FusionSkeleton'

import { exportKgEvidence, fetchReports, openReportUrl, exportGraphJson, exportGraphCsv, exportGraphMl, exportReportJson, exportCasePackage } from './report-api'
import { REPORT_REGISTRY, type ReportExportKind } from './report-registry'

type Props = {
  caseRef: string
  caseId?: string | null
  className?: string
}

export function ExportCenter({ caseRef, caseId, className }: Props) {
  const reportsQuery = useQuery({
    queryKey: ['fusion', 'reports', caseRef],
    queryFn: () => fetchReports(caseRef),
    retry: false,
  })

  const evidenceExport = useMutation({
    mutationFn: () => exportKgEvidence(caseRef),
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${caseRef}-evidence.json`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(fusionCopy.reports.exportReady)
    },
    onError: () => toast.error(fusionCopy.reports.exportFailed),
  })

  const clientExport = useMutation({
    mutationFn: async (kind: ReportExportKind) => {
      if (!caseId) throw new Error('no case')
      const graph = kind === 'graph-csv' || kind === 'graphml' || kind === 'case-package'
        ? await complianceService.getGraph(caseId)
        : null
      switch (kind) {
        case 'graph-json':
          return exportGraphJson(caseId, caseRef)
        case 'graph-csv':
          return exportGraphCsv(caseId, caseRef, graph)
        case 'graphml':
          return exportGraphMl(caseId, caseRef, graph)
        case 'report-json':
          return exportReportJson(caseId, caseRef)
        case 'case-package':
          return exportCasePackage(caseId, caseRef, graph)
        default:
          return evidenceExport.mutateAsync()
      }
    },
    onSuccess: () => toast.success(fusionCopy.reports.exportReady),
    onError: () => toast.error(fusionCopy.reports.exportFailed),
  })

  const handleExport = (kind: ReportExportKind) => {
    if (!caseId) {
      toast.error(fusionCopy.reports.noCaseId)
      return
    }
    if (kind === 'evidence-json') {
      evidenceExport.mutate()
      return
    }
    const entry = REPORT_REGISTRY.find((r) => r.id === kind)
    if (entry?.clientExport) {
      clientExport.mutate(kind)
    }
  }

  const items = reportsQuery.data ?? []

  return (
    <div className={cn('fusion-report-export', className)} data-testid="fusion-export-center">
      <header className="fusion-report-export__header">
        <h2 className="fusion-text-section">{fusionCopy.reports.exportHub}</h2>
        <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
          {fusionCopy.reports.exportHubDescription}
        </p>
      </header>

      <div className="fusion-report-export__grid">
        {REPORT_REGISTRY.map((entry) => (
          <article key={entry.id} className="fusion-report-export__card">
            <div className="fusion-report-export__card-head">
              <FileText className="h-4 w-4 text-[var(--fusion-ops-blue)]" aria-hidden />
              <h3 className="fusion-text-micro font-medium">{entry.label}</h3>
            </div>
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">{entry.description}</p>
            <button
              type="button"
              className="fusion-report-export__action"
              disabled={!caseId && entry.id !== 'evidence-json'}
              onClick={() => handleExport(entry.id)}
            >
              <Download className="h-3 w-3" aria-hidden />
              {(entry.id === 'evidence-json' && evidenceExport.isPending) ||
              (entry.clientExport && clientExport.isPending && clientExport.variables === entry.id)
                ? fusionCopy.reports.exporting
                : fusionCopy.reports.download}
            </button>
          </article>
        ))}
      </div>

      <section className="fusion-report-export__history">
        <h3 className="fusion-text-micro text-[var(--fusion-text-tertiary)] uppercase tracking-wider">
          {fusionCopy.reports.generatedReports}
        </h3>
        {reportsQuery.isLoading ? (
          <FusionSkeleton variant="row" className="mt-2" />
        ) : reportsQuery.isError ? (
          <FusionInlineError message={fusionCopy.reports.loadFailed} />
        ) : items.length === 0 ? (
          <FusionEmptyState
            title={fusionCopy.reports.emptyTitle}
            description={fusionCopy.reports.emptyDescription}
          />
        ) : (
          <ul className="fusion-report-export__list">
            {items.map((row) => {
              const pdfCaseId = row.case_id || caseId
              return (
                <li key={row.report_id ?? `${row.case_id}-${row.generated_at}`} className="fusion-report-export__row">
                  <div>
                    <span className="fusion-mono fusion-text-micro text-[var(--fusion-ops-blue)]">
                      {row.typology_code ?? row.report_id ?? 'report'}
                    </span>
                    <span className="fusion-text-micro text-[var(--fusion-text-tertiary)] ml-2">
                      {row.risk_level ?? row.decision_ru ?? '—'}
                    </span>
                    {row.generated_at ? (
                      <span className="fusion-text-micro text-[var(--fusion-text-tertiary)] ml-2">
                        {new Date(row.generated_at).toLocaleString('ru-RU')}
                      </span>
                    ) : null}
                  </div>
                  {pdfCaseId ? (
                    <button
                      type="button"
                      className="fusion-text-micro text-[var(--fusion-ops-blue)] inline-flex items-center gap-1"
                      onClick={() => {
                        void openReportUrl(`/api/compliance/cases/${pdfCaseId}/report.pdf`).catch(
                          () => toast.error(fusionCopy.reports.exportFailed)
                        )
                      }}
                    >
                      PDF <ExternalLink className="h-3 w-3" />
                    </button>
                  ) : null}
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
        <Link
          to="/dashboard/fusion/investigation/$caseRef"
          params={{ caseRef }}
          className="text-[var(--fusion-ops-blue)]"
        >
          ← {fusionCopy.reports.backToInvestigation}
        </Link>
      </p>
    </div>
  )
}
