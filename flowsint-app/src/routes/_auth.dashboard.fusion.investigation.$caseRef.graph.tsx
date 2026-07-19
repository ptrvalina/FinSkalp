import { useCallback, useMemo, useState } from 'react'
// highlightNodeIds must be referentially stable — new [] each render loops setNodes

import { useQuery } from '@tanstack/react-query'

import { createFileRoute } from '@tanstack/react-router'

import { complianceService } from '@/api/compliance-service'

import { useComplianceEvents } from '@/hooks/use-compliance-events'

import { FusionShell, FusionGraphStage, useFusionBroadcastSync } from '@/fusion'

import { buildInvestigationMissionStrip } from '@/fusion/fusion-mission-data'

export const Route = createFileRoute('/_auth/dashboard/fusion/investigation/$caseRef/graph')({
  component: FusionDetachedGraphPage,
})

function FusionDetachedGraphPage() {
  const { caseRef } = Route.useParams()
  const { liveEvents, graphAlerts } = useComplianceEvents({ enabled: true })
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [replayIndex, setReplayIndex] = useState(0)
  const [hopLensMaxDepth, setHopLensMaxDepth] = useState<number | null>(null)

  const casesQuery = useQuery({
    queryKey: ['fusion', 'cases'],
    queryFn: () => complianceService.listCases(),
  })

  const matchedCase = useMemo(
    () => casesQuery.data?.find((c) => c.case_ref === caseRef),
    [casesQuery.data, caseRef]
  )

  const caseId = matchedCase?.id

  const caseQuery = useQuery({
    queryKey: ['fusion', 'case', caseId],
    queryFn: () => complianceService.getCase(caseId!),
    enabled: Boolean(caseId),
  })

  const graphQuery = useQuery({
    queryKey: ['fusion', 'graph', caseId],
    queryFn: () => complianceService.getGraph(caseId!),
    enabled: Boolean(caseId),
  })

  const crossLinksQuery = useQuery({
    queryKey: ['fusion', 'cross-links', caseRef],
    queryFn: () => complianceService.getCrossCaseGraphLinks(caseRef),
    retry: false,
  })

  useFusionBroadcastSync(caseRef, { selectedNodeId, replayIndex }, (remote) => {
    setSelectedNodeId(remote.selectedNodeId)
    setReplayIndex(remote.replayIndex)
  })

  const handleNodeSelect = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId)
  }, [])

  const highlightNodeIds = useMemo(
    () => (selectedNodeId ? [selectedNodeId] : []),
    [selectedNodeId]
  )

  const mission = useMemo(
    () =>
      buildInvestigationMissionStrip({
        caseRef,
        caseData: caseQuery.data ?? matchedCase ?? null,
        graph: graphQuery.data,
        liveEvents,
      }),
    [caseRef, caseQuery.data, matchedCase, graphQuery.data, liveEvents]
  )

  const fusionDone = Boolean(caseQuery.data?.fusion_result)

  return (
    <FusionShell
      mission={mission}
      activeSection="graph"
      caseRef={caseRef}
      showStrPipeline
      workflowStatus={caseQuery.data?.workflow_status ?? matchedCase?.workflow_status}
      fusionDone={fusionDone}
    >
      <FusionGraphStage
        graph={graphQuery.data}
        loading={graphQuery.isLoading}
        alerts={graphAlerts}
        caseRef={caseRef}
        live={liveEvents.length > 0}
        persistent
        crossCaseLinks={crossLinksQuery.data?.links ?? []}
        selectedNodeId={selectedNodeId}
        onNodeSelect={handleNodeSelect}
        highlightNodeIds={highlightNodeIds}
        replayIndex={replayIndex}
        onReplayIndexChange={setReplayIndex}
        hopLensMaxDepth={hopLensMaxDepth}
        onHopLensMaxDepthChange={setHopLensMaxDepth}
        hopLensOriginId={selectedNodeId}
        className="h-full min-h-[100vh]"
      />
    </FusionShell>
  )
}
