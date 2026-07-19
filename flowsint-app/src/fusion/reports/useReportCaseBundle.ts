import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { complianceService } from '@/api/compliance-service'

import type { ReportCaseBundle, ReportDataKey } from './report-types'
import { fetchReportJson, fetchReports } from './report-api'

function extractInvestigatePayload(
  fusion: Record<string, unknown> | null,
  reportJson: Record<string, unknown> | null | undefined
): Record<string, unknown> | null {
  const sar =
    (reportJson?.sar_report as Record<string, unknown> | undefined) ??
    (fusion?.sar_report as Record<string, unknown> | undefined)
  if (sar && Object.keys(sar).length) {
    return {
      sar_report: sar,
      summary_ru: reportJson?.summary_ru ?? fusion?.executive_summary_ru,
      risk_score: reportJson?.risk_score ?? fusion?.illegal_flow_score,
      risk_level: reportJson?.risk_level ?? fusion?.risk_level,
      phases: reportJson?.phases,
      screening: reportJson?.screening ?? fusion?.screening,
    }
  }
  if (reportJson?.phases || reportJson?.screening) return reportJson
  return null
}

function hasFusion(
  data: Record<string, unknown> | null | undefined,
  status?: string | null
): boolean {
  if (status === 'fused') return true
  if (!data) return false
  return Boolean(
    data.executive_summary_ru ||
      data.illegal_flow_score != null ||
      data.evidence_graph ||
      data.findings ||
      data.decision_ru ||
      Array.isArray(data.attributions) ||
      Array.isArray(data.bridges) ||
      Array.isArray(data.hypotheses)
  )
}

export function useReportCaseBundle(caseRef: string): ReportCaseBundle {
  const casesQuery = useQuery({
    queryKey: ['compliance', 'cases'],
    queryFn: () => complianceService.listCases(),
  })

  const matched = casesQuery.data?.find(
    (c) => c.case_ref === caseRef || c.id === caseRef
  )
  const caseId = matched?.id ?? null

  const caseQuery = useQuery({
    queryKey: ['compliance', 'case', caseId],
    queryFn: () => complianceService.getCase(caseId!),
    enabled: Boolean(caseId),
    retry: false,
  })

  const graphQuery = useQuery({
    queryKey: ['compliance', 'graph', caseId],
    queryFn: () => complianceService.getGraph(caseId!),
    enabled: Boolean(caseId),
    retry: false,
    staleTime: 0,
    refetchOnMount: 'always',
  })

  const evidenceQuery = useQuery({
    queryKey: ['platform', 'evidence', caseRef],
    queryFn: () => complianceService.listInvestigationEvidence(caseRef),
    retry: false,
  })

  const timelineQuery = useQuery({
    queryKey: ['platform', 'timeline', caseRef],
    queryFn: () => complianceService.getCaseTimeline(caseRef),
    retry: false,
  })

  const workspaceQuery = useQuery({
    queryKey: ['platform', 'workspace', caseRef],
    queryFn: () => complianceService.getAnalystWorkspaceState({ caseRef }),
    retry: false,
  })

  const reportsQuery = useQuery({
    queryKey: ['compliance', 'reports', caseRef],
    queryFn: () => fetchReports(caseRef),
    retry: false,
  })

  const riskQuery = useQuery({
    queryKey: ['compliance', 'risk-history', caseId],
    queryFn: () => complianceService.getCaseRiskHistory(caseId!),
    enabled: Boolean(caseId),
    retry: false,
  })

  const crossQuery = useQuery({
    queryKey: ['compliance', 'cross-links', caseRef],
    queryFn: () => complianceService.getCrossCaseGraphLinks(caseRef),
    retry: false,
  })

  const fusion = (caseQuery.data?.fusion_result ?? null) as Record<string, unknown> | null
  const caseStatus = caseQuery.data?.status ?? (matched as { status?: string } | undefined)?.status

  const reportJsonQuery = useQuery({
    queryKey: ['compliance', 'report-json', caseId],
    queryFn: () => fetchReportJson(caseId!),
    enabled: Boolean(caseId) && hasFusion(fusion, caseStatus),
    retry: false,
  })

  const graph = graphQuery.data ?? null
  const evidenceItems = evidenceQuery.data?.items ?? workspaceQuery.data?.evidence?.items ?? []
  const timelineEvents = timelineQuery.data?.events ?? workspaceQuery.data?.timeline?.events ?? []

  const investigate = useMemo(
    () => extractInvestigatePayload(fusion, reportJsonQuery.data),
    [fusion, reportJsonQuery.data]
  )

  const readiness = useMemo((): Record<ReportDataKey, boolean> => {
    const graphNodes = graph?.nodes?.length ?? 0
    const fusionGraph =
      (fusion?.evidence_graph as { nodes?: unknown[] } | undefined)?.nodes?.length ?? 0
    return {
      case: Boolean(caseId && matched),
      fusion: hasFusion(fusion, caseStatus),
      graph: graphNodes > 0 || fusionGraph > 0,
      evidence: evidenceItems.length > 0,
      timeline: timelineEvents.length > 0,
      kyt: Boolean(
        fusion?.risk_level ||
          (fusion?.metrics as Record<string, unknown> | undefined)?.kyt ||
          reportsQuery.data?.some((r) => r.risk_level)
      ),
      crossCase: (crossQuery.data?.count ?? 0) > 0,
      riskHistory: (riskQuery.data?.points?.length ?? 0) > 0,
      generatedReports: (reportsQuery.data?.length ?? 0) > 0,
    }
  }, [
    caseId,
    matched,
    caseStatus,
    fusion,
    graph,
    evidenceItems.length,
    timelineEvents.length,
    crossQuery.data,
    riskQuery.data,
    reportsQuery.data,
  ])

  const loading =
    casesQuery.isLoading ||
    (Boolean(caseId) && caseQuery.isLoading) ||
    graphQuery.isLoading

  const error =
    (casesQuery.isError && 'Не удалось загрузить дела') ||
    (caseQuery.isError && 'Дело недоступно') ||
    null

  return {
    caseRef,
    caseId,
    caseRow: (caseQuery.data ?? matched ?? null) as Record<string, unknown> | null,
    fusion,
    graph: graph
      ? { nodes: graph.nodes ?? [], edges: graph.edges ?? [] }
      : fusion?.evidence_graph
        ? {
            nodes: (fusion.evidence_graph as { nodes?: unknown[] }).nodes ?? [],
            edges: (fusion.evidence_graph as { edges?: unknown[] }).edges ?? [],
          }
        : null,
    evidence: { count: evidenceItems.length, items: evidenceItems },
    timeline: { count: timelineEvents.length, events: timelineEvents },
    riskHistory: { points: riskQuery.data?.points ?? [] },
    crossCase: {
      links: crossQuery.data?.links ?? [],
      count: crossQuery.data?.count ?? 0,
    },
    generatedReports: reportsQuery.data ?? [],
    workspace: (workspaceQuery.data ?? null) as Record<string, unknown> | null,
    investigate,
    loading,
    error: typeof error === 'string' ? error : null,
    readiness,
  }
}
