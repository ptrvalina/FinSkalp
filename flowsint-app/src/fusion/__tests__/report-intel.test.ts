import { describe, expect, it } from 'vitest'

import { deriveExecutiveSummary, deriveReportRisk } from '../reports/report-intel'
import type { ReportCaseBundle } from '../reports/report-types'

function bundle(partial: Partial<ReportCaseBundle>): ReportCaseBundle {
  return {
    caseRef: 'WL-TEST',
    caseId: '1',
    caseRow: { status: 'fused' },
    fusion: null,
    graph: null,
    evidence: { count: 0, items: [] },
    timeline: { count: 0, events: [] },
    riskHistory: { points: [] },
    crossCase: { links: [], count: 0 },
    generatedReports: [],
    workspace: null,
    investigate: null,
    loading: false,
    error: null,
    readiness: {
      case: true,
      fusion: true,
      graph: true,
      evidence: false,
      timeline: false,
      kyt: false,
      crossCase: false,
      riskHistory: false,
      generatedReports: false,
    },
    ...partial,
  }
}

describe('report-intel', () => {
  it('derives risk from graph + hypotheses when fusion scores missing', () => {
    const r = deriveReportRisk(
      bundle({
        fusion: {
          hypotheses: [{ confidence: 0.55, statement_ru: 'OSINT cluster' }],
        },
        graph: {
          nodes: [
            { id: 'w1', kind: 'wallet', confidence: 0.7 },
            { id: 'm1', kind: 'osint_mention', confidence: 0.8 },
            { id: 'm2', kind: 'osint_mention', confidence: 0.6 },
          ],
          edges: [
            { id: 'e1', source: 'w1', target: 'm1', rel_type: 'OSINT_MENTION', strength: 0.8 },
            { id: 'e2', source: 'w1', target: 'm2', rel_type: 'OSINT_MENTION', strength: 0.7 },
          ],
        },
      })
    )
    expect(r.score).toBeGreaterThan(20)
    expect(r.level).toBeTruthy()
    expect(r.source).toBe('derived')
  })

  it('builds executive summary from graph when no fusion text', () => {
    const text = deriveExecutiveSummary(
      bundle({
        fusion: {
          hypotheses: [{ confidence: 0.55, statement_ru: 'Есть OSINT следы' }],
        },
        graph: {
          nodes: [
            { id: 'w1', kind: 'wallet', label: 'tron:TJp8BkZe', confidence: 0.7 },
            { id: 'm1', kind: 'osint_mention', confidence: 0.8 },
          ],
          edges: [{ id: 'e1', source: 'w1', target: 'm1', rel_type: 'OSINT_MENTION' }],
        },
      })
    )
    expect(text).toContain('WL-TEST')
    expect(text).toContain('OSINT')
    expect(text).toContain('риск')
  })
})
