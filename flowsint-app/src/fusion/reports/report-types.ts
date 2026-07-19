/** Canonical Report Center type system — FinSkalp Reporting OS */

export type ReportCategory =
  | 'intelligence'
  | 'evidence'
  | 'financial'
  | 'entity'
  | 'osint'
  | 'compliance'
  | 'analysis'
  | 'export'

export type ReportDataKey =
  | 'case'
  | 'fusion'
  | 'graph'
  | 'evidence'
  | 'timeline'
  | 'kyt'
  | 'crossCase'
  | 'riskHistory'
  | 'generatedReports'

export type ReportSectionId =
  | 'cover'
  | 'classification'
  | 'metadata'
  | 'case-info'
  | 'executive-summary'
  | 'mission-summary'
  | 'network-overview'
  | 'graph-snapshot'
  | 'entity-table'
  | 'relationship-table'
  | 'timeline'
  | 'evidence'
  | 'wallet-profile'
  | 'money-flow'
  | 'osint-mentions'
  | 'sanctions-exposure'
  | 'attribution-ownership'
  | 'risk'
  | 'compliance-checklist'
  | 'recommendations'
  | 'analyst-notes'
  | 'chain-of-custody'
  | 'appendices'
  | 'signature'
  | 'export-actions'

export type ReportModuleId =
  | 'executive-brief'
  | 'complete-investigation'
  | 'evidence-dossier'
  | 'wallet-intelligence'
  | 'money-flow'
  | 'entity-profile'
  | 'osint-intelligence'
  | 'cross-case'
  | 'risk-assessment'
  | 'compliance'
  | 'fz115'
  | 'aml'
  | 'kyt'
  | 'travel-rule'
  | 'blockchain-analysis'
  | 'executive-summary'
  | 'analyst-summary'
  | 'chain-of-custody'
  | 'timeline'
  | 'network-intelligence'
  | 'graph-intelligence'
  | 'cluster'
  | 'attribution'
  | 'relationship'
  | 'case-review'
  | 'recommendation'
  | 'str'
  | 'sar'
  | 'pdf-preview'
  | 'presentation-mode'
  | 'export-center'

export type ReportModuleDef = {
  id: ReportModuleId
  label: string
  labelRu: string
  category: ReportCategory
  description: string
  glyph: string
  /** At least one key must be satisfied (non-empty) for "ready" state */
  requiresAny: ReportDataKey[]
  /** All keys must be present for full report */
  requiresAll?: ReportDataKey[]
  sections: ReportSectionId[]
  pdfExport?: boolean
  presentation?: boolean
}

export type ReportCaseBundle = {
  caseRef: string
  caseId: string | null
  caseRow: Record<string, unknown> | null
  fusion: Record<string, unknown> | null
  graph: { nodes: unknown[]; edges: unknown[] } | null
  evidence: { count: number; items: unknown[] }
  timeline: { count: number; events: unknown[] }
  riskHistory: { points: Array<{ ts: string; score: number; source?: string }> }
  crossCase: { links: unknown[]; count: number }
  generatedReports: unknown[]
  workspace: Record<string, unknown> | null
  investigate: Record<string, unknown> | null
  loading: boolean
  error: string | null
  readiness: Record<ReportDataKey, boolean>
}
