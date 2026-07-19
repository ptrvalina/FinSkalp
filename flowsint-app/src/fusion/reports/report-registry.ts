import { complianceService } from '@/api/compliance-service'

export type ReportExportKind =
  | 'pdf'
  | 'xlsx'
  | 'fz115-json'
  | 'fz115-xml'
  | 'evidence-json'
  | 'report-json'
  | 'graph-json'
  | 'graph-csv'
  | 'graphml'
  | 'case-package'

export type ReportRegistryEntry = {
  id: ReportExportKind
  label: string
  description: string
  mime: string
  buildUrl: (caseId: string, caseRef?: string) => string | null
  download?: boolean
  clientExport?: boolean
}

export const REPORT_REGISTRY: ReportRegistryEntry[] = [
  {
    id: 'pdf',
    label: 'Investigation PDF',
    description: 'Единый регуляторный PDF (не модуль Report Center)',
    mime: 'application/pdf',
    buildUrl: (caseId) => complianceService.reportPdfUrl(caseId),
    download: true,
  },
  {
    id: 'xlsx',
    label: 'Investigation XLSX',
    description: 'Табличный экспорт транзакций и сущностей',
    mime: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    buildUrl: (caseId) => complianceService.reportXlsxUrl(caseId),
    download: true,
  },
  {
    id: 'fz115-json',
    label: '115-ФЗ JSON',
    description: 'Структурированная подача 115-ФЗ',
    mime: 'application/json',
    buildUrl: (caseId) => complianceService.fz115ReportUrl(caseId, 'json'),
    download: true,
  },
  {
    id: 'fz115-xml',
    label: '115-ФЗ XML',
    description: 'XML-пакет для регуляторной подачи',
    mime: 'application/xml',
    buildUrl: (caseId) => complianceService.fz115ReportUrl(caseId, 'xml'),
    download: true,
  },
  {
    id: 'report-json',
    label: 'Report JSON',
    description: 'Полный fusion_result / report.json',
    mime: 'application/json',
    buildUrl: (caseId) => complianceService.reportJsonUrl(caseId),
    clientExport: true,
  },
  {
    id: 'graph-json',
    label: 'Graph JSON',
    description: 'Evidence graph (fusion + Neo4j fallback)',
    mime: 'application/json',
    buildUrl: () => null,
    clientExport: true,
  },
  {
    id: 'graph-csv',
    label: 'Nodes CSV',
    description: 'Таблица сущностей графа',
    mime: 'text/csv',
    buildUrl: () => null,
    clientExport: true,
  },
  {
    id: 'graphml',
    label: 'GraphML',
    description: 'GraphML для Gephi / yEd',
    mime: 'application/xml',
    buildUrl: () => null,
    clientExport: true,
  },
  {
    id: 'evidence-json',
    label: 'Evidence bundle',
    description: 'Экспорт KG-доказательств (JSON через API)',
    mime: 'application/json',
    buildUrl: () => null,
    clientExport: true,
  },
  {
    id: 'case-package',
    label: 'Case package',
    description: 'Report + evidence + graph metadata',
    mime: 'application/json',
    buildUrl: () => null,
    clientExport: true,
  },
]

export function reportEntry(id: ReportExportKind): ReportRegistryEntry | undefined {
  return REPORT_REGISTRY.find((r) => r.id === id)
}
