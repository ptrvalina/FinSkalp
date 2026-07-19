import type {
  ComplianceCase,
  EvidenceGraph,
  RiskHistoryPoint,
  WorkflowStats,
} from '@/api/compliance-service'
import type { FusionMissionStripData } from './FusionMissionStrip'

export const FUSION_LAST_CASE_KEY = 'fusion-last-case-ref'

export const WORKFLOW_LABELS: Record<string, string> = {
  new: 'НОВЫЙ STR',
  scoring: 'СКОРИНГ',
  fusion: 'OSINT FUSION',
  graph: 'ГРАФ СВЯЗЕЙ',
  hypotheses: 'ГИПОТЕЗЫ',
  evidence: 'ДОКАЗАТЕЛЬСТВА',
  review: 'ОЦЕНКА РИСКА',
  recommendation: 'РЕКОМЕНДАЦИЯ',
  filed: 'SAR / ОТЧЁТ',
  triage: 'ТРИАЖ',
  investigating: 'РАССЛЕДОВАНИЕ',
  pending_filing: 'К ПОДАЧЕ',
  archived: 'АРХИВ',
}

type InboxRow = {
  case_id?: string
  case_ref?: string
  title_ru?: string
  priority?: string
  workflow_status?: string
  sla_breached?: boolean
}

type WorkspaceSlice = {
  evidence?: { count?: number }
  timeline?: { count?: number }
  counts?: { evidence?: number; timeline?: number }
  intelligence?: { supported_chains?: string[] }
}

type LiveEvent = { text_ru?: string; type?: string }

export function saveLastCaseRef(caseRef: string) {
  try {
    localStorage.setItem(FUSION_LAST_CASE_KEY, caseRef)
  } catch {
    /* ignore */
  }
}

export function loadLastCaseRef(): string | null {
  try {
    return localStorage.getItem(FUSION_LAST_CASE_KEY)
  } catch {
    return null
  }
}

export function fusionConfidenceLabel(fusion?: Record<string, unknown> | null): string | undefined {
  if (!fusion) return undefined
  const raw =
    fusion.confidence ??
    fusion.aggregate_confidence ??
    (fusion.confidence_dimensions as Record<string, unknown> | undefined)?.aggregate_risk_score
  if (raw == null) return undefined
  const n = Number(raw)
  if (!Number.isFinite(n)) return String(raw)
  if (n <= 1) return `${Math.round(n * 100)}%`
  return `${Math.round(n)}%`
}

export function fusionEvidenceQuality(fusion?: Record<string, unknown> | null): string | undefined {
  if (!fusion) return undefined
  const metrics = fusion.metrics as Record<string, unknown> | undefined
  const raw =
    metrics?.evidence_quality ??
    metrics?.evidence_strength ??
    fusion.evidence_quality ??
    fusion.evidence_strength
  if (raw == null) return undefined
  const n = Number(raw)
  if (Number.isFinite(n) && n <= 1) return `${Math.round(n * 100)}%`
  if (Number.isFinite(n)) return `${Math.round(n)}%`
  return String(raw)
}

export function fusionHypothesesCount(fusion?: Record<string, unknown> | null): number | undefined {
  if (!fusion) return undefined
  const h = fusion.hypotheses
  if (Array.isArray(h)) return h.length
  if (typeof fusion.hypotheses_count === 'number') return fusion.hypotheses_count
  return undefined
}

export function countGraphWallets(graph?: EvidenceGraph | null): number | undefined {
  if (!graph?.nodes?.length) return undefined
  const n = graph.nodes.filter((node) => {
    const kind = (node.kind ?? '').toLowerCase()
    const label = (node.label ?? '').toLowerCase()
    return (
      kind.includes('wallet') ||
      kind.includes('address') ||
      label.startsWith('t') ||
      label.startsWith('0x')
    )
  }).length
  return n || undefined
}

export function graphTxVelocity(graph?: EvidenceGraph | null): string | undefined {
  if (!graph?.edges?.length) return undefined
  const tsEdges = graph.edges.filter((e) => {
    const meta = e as { timestamp?: string; ts?: string; occurred_at?: string }
    return meta.timestamp ?? meta.ts ?? meta.occurred_at
  }).length
  if (tsEdges > 0) return `${tsEdges}/${graph.edges.length} timed`
  return `${graph.edges.length} tx`
}

export function formatRiskEvolution(
  points?: RiskHistoryPoint[],
  trend?: string | null
): string | undefined {
  if (trend) return trend
  if (!points?.length) return undefined
  const last = points[points.length - 1]?.score
  if (points.length === 1 && last != null) return String(last)
  const first = points[0]?.score
  if (first == null || last == null) return undefined
  const delta = last - first
  if (delta > 0) return `↑ ${last.toFixed(0)}`
  if (delta < 0) return `↓ ${last.toFixed(0)}`
  return `→ ${last.toFixed(0)}`
}

export function dominantPipelineStage(pipeline: Record<string, number>): string | undefined {
  const entries = Object.entries(pipeline)
  if (!entries.length) return undefined
  const [stage, count] = entries.sort((a, b) => b[1] - a[1])[0]
  return `${stage}:${count}`
}

export function buildCommandMissionStrip(params: {
  stats?: WorkflowStats | null
  inbox?: InboxRow[]
  previewCase?: ComplianceCase | null
  graph?: EvidenceGraph | null
  riskHistory?: { points?: RiskHistoryPoint[]; trend?: string | null } | null
  recommendationsCount?: number
  liveEvents?: LiveEvent[]
}): FusionMissionStripData {
  const { stats, inbox = [], previewCase, graph, riskHistory, recommendationsCount, liveEvents = [] } =
    params
  const previewInbox = inbox[0]
  const fusion = previewCase?.fusion_result as Record<string, unknown> | null | undefined
  const pipeline = stats?.pipeline ?? {}

  return {
    objective:
      previewInbox?.title_ru ??
      previewInbox?.case_ref ??
      (stats?.total != null ? `${stats.total} cases` : undefined),
    threat:
      stats?.sla_breached != null && stats.sla_breached > 0
        ? `SLA ${stats.sla_breached}`
        : previewInbox?.priority ?? previewCase?.priority,
    status: dominantPipelineStage(pipeline) ?? 'COMMAND',
    intelligence: liveEvents[0]?.text_ru ?? liveEvents[0]?.type,
    hypotheses: fusionHypothesesCount(fusion),
    evidenceQuality: fusionEvidenceQuality(fusion),
    confidence: fusionConfidenceLabel(fusion) ?? meanGraphConfidence(graph),
    entities: graph?.nodes?.length,
    wallets: countGraphWallets(graph),
    txVelocity: graphTxVelocity(graph),
    riskEvolution: formatRiskEvolution(riskHistory?.points, riskHistory?.trend),
    timeline: undefined,
    recommendations: recommendationsCount,
    queue: inbox.length || stats?.total,
  }
}

export function buildInvestigationMissionStrip(params: {
  caseRef: string
  caseData?: ComplianceCase | null
  workflowStatus?: string | null
  graph?: EvidenceGraph | null
  workspace?: WorkspaceSlice | null
  riskHistory?: { points?: RiskHistoryPoint[]; trend?: string | null } | null
  recommendationsCount?: number
  queuePosition?: number | null
  liveEvents?: LiveEvent[]
}): FusionMissionStripData {
  const {
    caseRef,
    caseData,
    workflowStatus,
    graph,
    workspace,
    riskHistory,
    recommendationsCount,
    queuePosition,
    liveEvents = [],
  } = params
  const wf = workflowStatus ?? caseData?.workflow_status
  const fusion = caseData?.fusion_result as Record<string, unknown> | null | undefined

  return {
    objective: caseRef,
    threat: caseData?.priority ?? (caseData?.sla_breached ? 'SLA BREACH' : undefined),
    status: WORKFLOW_LABELS[wf ?? ''] ?? wf,
    intelligence: liveEvents[0]?.text_ru ?? liveEvents[0]?.type,
    hypotheses: fusionHypothesesCount(fusion),
    evidenceQuality:
      fusionEvidenceQuality(fusion) ??
      (workspace?.evidence?.count ?? workspace?.counts?.evidence),
    confidence: fusionConfidenceLabel(fusion) ?? meanGraphConfidence(graph),
    entities: graph?.nodes?.length,
    wallets: countGraphWallets(graph),
    txVelocity: graphTxVelocity(graph),
    riskEvolution:
      formatRiskEvolution(riskHistory?.points, riskHistory?.trend) ??
      (caseData?.sla_breached ? 'SLA BREACH' : undefined),
    timeline: workspace?.timeline?.count ?? workspace?.counts?.timeline,
    recommendations: recommendationsCount,
    queue: queuePosition ?? undefined,
  }
}

function meanGraphConfidence(graph?: EvidenceGraph | null): string | undefined {
  if (!graph?.nodes?.length) return undefined
  const vals = graph.nodes
    .map((n) => n.confidence)
    .filter((c): c is number => typeof c === 'number' && !Number.isNaN(c))
  if (!vals.length) return undefined
  return `${((vals.reduce((a, b) => a + b, 0) / vals.length) * 100).toFixed(0)}%`
}
