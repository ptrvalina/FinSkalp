import { useQuery } from '@tanstack/react-query'
import { ExternalLink, FileText } from 'lucide-react'

import { complianceService } from '@/api/compliance-service'
import { EnterprisePanel } from '@/components/enterprise/enterprise-ui'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

type Props = {
  caseRef: string
  caseId?: string | null
  evidenceCount?: number
  fusionResult?: Record<string, unknown> | null
}

function fusionConfidence(fusion: Record<string, unknown> | null | undefined): string | null {
  if (!fusion) return null
  const raw =
    fusion.confidence ??
    fusion.aggregate_confidence ??
    (fusion.confidence_dimensions as Record<string, unknown> | undefined)?.aggregate_risk_score
  if (raw == null) return null
  const n = Number(raw)
  if (Number.isFinite(n) && n <= 1) return `${Math.round(n * 100)}%`
  if (Number.isFinite(n)) return `${Math.round(n)}%`
  return String(raw)
}

export function FusionReportsPanel({ caseRef, caseId, evidenceCount, fusionResult }: Props) {
  const reportsQuery = useQuery({
    queryKey: ['compliance', 'reports', caseRef],
    queryFn: () => complianceService.listReports(caseRef),
    retry: false,
  })

  const items = reportsQuery.data ?? []
  const confidence = fusionConfidence(fusionResult)
  const livingPreview = {
    evidence: evidenceCount ?? '—',
    confidence: confidence ?? '—',
    reports: items.length,
    risk: fusionResult?.risk_level ?? fusionResult?.decision_ru ?? '—',
  }

  return (
    <EnterprisePanel
      title="Отчёты 115-ФЗ"
      description="Living report object — evidence, confidence, and generated filings."
    >
      <div className="mb-4 grid gap-2 sm:grid-cols-4">
        <PreviewMetric label="Evidence" value={String(livingPreview.evidence)} />
        <PreviewMetric label="Confidence" value={String(livingPreview.confidence)} />
        <PreviewMetric label="Reports" value={String(livingPreview.reports)} />
        <PreviewMetric label="Risk / decision" value={String(livingPreview.risk)} />
      </div>

      {reportsQuery.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : reportsQuery.isError ? (
        <p className="text-sm text-muted-foreground">
          Отчёты недоступны. Запустите fusion для кейса{' '}
          <span className="font-mono">{caseRef}</span>.
        </p>
      ) : items.length === 0 ? (
        <div className="space-y-3 text-sm">
          <p className="text-muted-foreground">
            {fusionResult
              ? 'Fusion завершён, но отчёт ещё не сгенерирован. Откройте Report Center.'
              : 'Отчёты появятся после этапа Fusion. Сейчас до этого этапа ещё не дошли.'}
          </p>
          <Button variant="outline" size="sm" asChild>
            <a href={`/dashboard/fusion/reports/${encodeURIComponent(caseRef)}`}>
              {fusionResult ? 'Открыть Report Center' : 'Этапы: Collect → KYT → Fusion → Отчёт'}
            </a>
          </Button>
        </div>
      ) : (
        <ul className="space-y-3 text-sm">
          {items.map((row) => {
            const pdfCaseId = row.case_id || caseId
            return (
              <li
                key={row.report_id ?? row.case_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-3"
              >
                <div>
                  <div className="font-medium flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    {row.report_id ?? row.case_ref ?? '—'}
                  </div>
                  <div className="text-muted-foreground text-xs mt-1">
                    {row.typology_code} · {row.decision_ru ?? '—'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {row.risk_level ? <Badge variant="outline">{row.risk_level}</Badge> : null}
                  {pdfCaseId ? (
                    <Button variant="outline" size="sm" asChild>
                      <a href={complianceService.reportPdfUrl(pdfCaseId)} target="_blank" rel="noreferrer">
                        PDF <ExternalLink className="w-3 h-3 ml-1" />
                      </a>
                    </Button>
                  ) : null}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </EnterprisePanel>
  )
}

function PreviewMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-panel)] px-2.5 py-2">
      <p className="text-[9px] uppercase tracking-wider text-[var(--fusion-text-tertiary)]">{label}</p>
      <p className="mt-0.5 font-mono text-sm font-semibold text-[var(--fusion-text-primary)] truncate">
        {value}
      </p>
    </div>
  )
}
