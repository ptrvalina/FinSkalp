import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { complianceService } from '@/api/compliance-service'
import { cn } from '@/lib/utils'

import { FusionEmptyState } from '../FusionEmptyState'
import { FusionInlineError } from '../FusionInlineError'
import { FusionSkeleton } from '../FusionSkeleton'
import { fusionCopy } from '../fusion-copy'

import { ExportCenter } from './ExportCenter'
import { isModuleReady, reportModule } from './report-catalog'
import { fetchReportBlob, openCurrentModulePdf, printCurrentModulePdf } from './report-api'
import { buildModuleFindings } from './report-module-findings'
import { ReportCover, ReportSectionBody, ReportToc } from './ReportDocumentSections'
import type { ReportCaseBundle, ReportModuleId } from './report-types'
import { useReportCaseBundle } from './useReportCaseBundle'

type Props = {
  caseRef: string
  reportType: ReportModuleId
  presentation?: boolean
}

export function ReportDocumentView({ caseRef, reportType, presentation = false }: Props) {
  const module = reportModule(reportType)
  const bundle = useReportCaseBundle(caseRef)

  if (reportType === 'export-center') {
    return (
      <ExportCenter
        caseRef={caseRef}
        caseId={bundle.caseId}
        className="fusion-report-export--embedded"
      />
    )
  }

  if (!module) {
    return (
      <FusionEmptyState
        className="m-6"
        title={fusionCopy.reports.unknownModule}
        description={reportType}
      />
    )
  }

  if (bundle.loading) return <FusionSkeleton variant="card" className="m-6" />

  const ready = isModuleReady(module, bundle.readiness)

  if (reportType === 'pdf-preview') {
    return (
      <ReportPdfPreview caseId={bundle.caseId} caseRef={caseRef} ready={ready && Boolean(bundle.caseId)} />
    )
  }

  const isPresentation = presentation || reportType === 'presentation-mode'

  return (
    <div
      className={cn(
        'fusion-report-doc',
        isPresentation && 'fusion-report-doc--presentation',
        !ready && 'fusion-report-doc--draft'
      )}
      data-testid="fusion-report-document"
    >
      <header className="fusion-report-doc__toolbar">
        <div>
          <h1 className="fusion-text-section">{module.labelRu}</h1>
          <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">{module.description}</p>
        </div>
        <div className="fusion-report-doc__toolbar-actions">
          {!ready ? (
            <span className="fusion-text-micro fusion-tone-warning uppercase">
              {fusionCopy.reports.awaitingData}
            </span>
          ) : null}
          {module.pdfExport ? (
            <button
              type="button"
              className="fusion-report-doc__btn"
              data-testid="fusion-report-pdf"
              title="Полный документ модуля → диалог печати → Сохранить как PDF"
              onClick={() => openCurrentModulePdf(module.labelRu, caseRef)}
            >
              PDF
            </button>
          ) : null}
          <button
            type="button"
            className="fusion-report-doc__btn"
            data-testid="fusion-report-print"
            title="Печать полного документа модуля (не Dashboard)"
            onClick={() => printCurrentModulePdf(module.labelRu, caseRef, { autoPrint: true })}
          >
            {fusionCopy.reports.print}
          </button>
        </div>
      </header>

      <div className="fusion-report-doc__layout">
        <ReportToc sections={module.sections} />
        <article className="fusion-report-doc__body">
          <ReportCover module={module} bundle={bundle} />
          <ReportModuleFindingsStrip reportType={reportType} bundle={bundle} />
          {module.sections.map((sectionId) => (
            <ReportSectionBody key={sectionId} sectionId={sectionId} bundle={bundle} />
          ))}
        </article>
      </div>
    </div>
  )
}

function ReportModuleFindingsStrip({
  reportType,
  bundle,
}: {
  reportType: ReportModuleId
  bundle: ReportCaseBundle
}) {
  const findings = buildModuleFindings(reportType, bundle)
  if (!findings.length) return null
  return (
    <section
      className="fusion-report-doc__findings"
      id="section-module-findings"
      data-testid="fusion-report-module-findings"
    >
      <h2 className="fusion-text-micro uppercase tracking-wider text-[var(--fusion-text-tertiary)]">
        Ключевые выводы модуля
      </h2>
      <ul className="fusion-report-doc__findings-list">
        {findings.map((f) => (
          <li key={f.title} data-tone={f.tone ?? 'muted'}>
            <strong>{f.title}</strong>
            <span>{f.detail}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function ReportPdfPreview({
  caseId,
  caseRef,
  ready,
}: {
  caseId: string | null
  caseRef: string
  ready: boolean
}) {
  const pdfQuery = useQuery({
    queryKey: ['fusion', 'report-pdf', caseId],
    queryFn: () => fetchReportBlob(complianceService.reportPdfUrl(caseId!)),
    enabled: Boolean(caseId) && ready,
    retry: false,
  })

  const [url, setUrl] = useState<string | null>(null)
  const [zoom, setZoom] = useState(100)

  useEffect(() => {
    if (!pdfQuery.data) return
    const objectUrl = URL.createObjectURL(pdfQuery.data)
    setUrl(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [pdfQuery.data])

  if (!caseId || !ready) {
    return (
      <FusionEmptyState
        className="m-6"
        title={fusionCopy.reports.emptyTitle}
        description={fusionCopy.reports.emptyDescription}
      />
    )
  }

  if (pdfQuery.isLoading) return <FusionSkeleton variant="card" className="m-6 h-[70vh]" />
  if (pdfQuery.isError) {
    return <FusionInlineError className="m-6" message={fusionCopy.reports.pdfUnavailable} />
  }

  return (
    <div className="fusion-report-pdf-preview" data-testid="fusion-report-pdf-preview">
      <header className="fusion-report-doc__toolbar">
        <h1 className="fusion-text-section">{fusionCopy.reports.pdfPreview}</h1>
        <span className="fusion-mono fusion-text-micro text-[var(--fusion-text-tertiary)]">{caseRef}</span>
        <div className="fusion-report-pdf-preview__zoom">
          <button type="button" className="fusion-report-doc__btn" onClick={() => setZoom((z) => Math.max(50, z - 10))}>
            −
          </button>
          <span className="fusion-mono fusion-text-micro">{zoom}%</span>
          <button type="button" className="fusion-report-doc__btn" onClick={() => setZoom((z) => Math.min(200, z + 10))}>
            +
          </button>
          <button type="button" className="fusion-report-doc__btn" onClick={() => setZoom(100)}>
            100%
          </button>
        </div>
      </header>
      {url ? (
        <div className="fusion-report-pdf-preview__viewport">
          <iframe
            title="Report PDF preview"
            src={url}
            className="fusion-report-pdf-preview__frame"
            style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top center' }}
          />
        </div>
      ) : null}
    </div>
  )
}
