import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useNavigate } from '@tanstack/react-router'

import { complianceService } from '@/api/compliance-service'

import { useComplianceEvents } from '@/hooks/use-compliance-events'

import { useFusionPermissions } from '@/hooks/use-fusion-permissions'

import {
  buildTimelineNodeMap,
  buildReplaySteps,
  replayIndexForEvent,
  cumulativeReplayHighlights,
  eventIdAtReplayIndex,
  useFusionBroadcastSync,
  subscribeFusionSync,
  useFusionLiveRefetchInterval,
  runMioBatch,
  readInvestigationSession,
  type FusionOpsLens,
} from '@/fusion'

import { useFusionInvestigationEvolution } from '@/fusion/useFusionInvestigationEvolution'

import { saveLastCaseRef } from '@/fusion/fusion-mission-data'

import {
  buildMioCards,
  extractDefaultWallet,
  type MioExecutableCard,
} from '@/fusion/fusion-mio-actions'

import { resolveDemoScenarioId } from '@/fusion/fusion-demo-scenarios'

import { executeMioCardAction } from '@/fusion/fusion-mio-execute'

import { openReportUrl } from '@/fusion/reports/report-api'

import { loadCaseSession, mergeCaseSession } from '@/fusion/fusion-case-session'

import { runInvestigationPipeline, retryInvestigationPipeline } from '@/fusion/fusion-investigation-start'

import { fusionLensFromSearch, fusionMissionSearch } from '@/fusion/fusion-route-search'

import { primaryWallet } from '@/fusion/fusion-investigation-seed'

import { fusionCopy } from '@/fusion/fusion-copy'

import type { FusionQueueRow } from '@/fusion/FusionQueuePanel'

import { toast } from 'sonner'

const STAGGER_MS = 120

export function useInvestigationWorkspace(caseRef: string, lensSearch?: FusionOpsLens) {
  const navigate = useNavigate()
  const sessionInit = useMemo(() => readInvestigationSession(caseRef), [caseRef])
  const queryClient = useQueryClient()
  const { liveEvents, graphAlerts } = useComplianceEvents({ enabled: true })

  const [leftTab, setLeftTab] = useState<'timeline' | 'hypotheses'>(sessionInit.leftTab)
  const [dismissedCards, setDismissedCards] = useState<string[]>([])
  const [sessionTick, setSessionTick] = useState(0)
  const caseSession = useMemo(() => {
    void sessionTick
    return loadCaseSession(caseRef)
  }, [caseRef, sessionTick])

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(sessionInit.selectedNodeId)
  const [selectedTimelineEventId, setSelectedTimelineEventId] = useState<string | null>(
    sessionInit.selectedTimelineEventId
  )
  const [replayIndex, setReplayIndex] = useState(sessionInit.replayIndex)
  const [hopLensMaxDepth, setHopLensMaxDepth] = useState<number | null>(sessionInit.hopLensMaxDepth)
  const [dockTab, setDockTab] = useState(sessionInit.dockTab)
  const [livePaused, setLivePausedState] = useState(sessionInit.livePaused)
  const [activeLens, setActiveLensState] = useState<FusionOpsLens>(() =>
    fusionLensFromSearch(lensSearch)
  )
  const [contextCollapsed, setContextCollapsed] = useState(false)
  const [batchRunning, setBatchRunning] = useState(false)
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number } | null>(
    null
  )
  const batchCancelRef = useRef(false)
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(
    sessionInit.selectedEvidenceId
  )
  const [queryReady, setQueryReady] = useState(false)
  const pipelineRunningRef = useRef(false)
  const [pipelineTick, setPipelineTick] = useState(0)

  const pipelineSession = useMemo(() => {
    void pipelineTick
    return loadCaseSession(caseRef)
  }, [caseRef, pipelineTick])

  const pipelineActive =
    pipelineSession.pipelineStatus === 'pending' || pipelineSession.pipelineStatus === 'running'

  const pipelinePhase = pipelineSession.pipelinePhase ?? null

  const graphContainerRef = useRef<HTMLDivElement>(null)
  const timelineItemRefs = useRef<Map<string, HTMLLIElement>>(new Map())

  useEffect(() => {
    return subscribeFusionSync((sync) => {
      if (sync.activeDockTab) setDockTab(sync.activeDockTab)
      setLivePausedState(sync.livePaused)
      if (sync.panelFocus === 'timeline') setLeftTab('timeline')
    })
  }, [])

  useEffect(() => {
    setActiveLensState(fusionLensFromSearch(lensSearch))
  }, [lensSearch])

  const setActiveLens = useCallback(
    (next: FusionOpsLens) => {
      setActiveLensState(next)
      navigate({
        to: '/dashboard/fusion/investigation/$caseRef',
        params: { caseRef },
        search: fusionMissionSearch(next === 'canvas' ? undefined : next),
        replace: true,
      })
    },
    [navigate, caseRef]
  )

  useEffect(() => {
    if (pipelineActive) setActiveLensState('canvas')
  }, [caseRef, pipelineActive])

  useEffect(() => {
    if (!pipelineActive) return
    const timer = window.setInterval(() => setPipelineTick((n) => n + 1), 600)
    return () => window.clearInterval(timer)
  }, [pipelineActive])

  useEffect(() => {
    setQueryReady(false)
    const t = window.setTimeout(() => setQueryReady(true), STAGGER_MS)
    return () => window.clearTimeout(t)
  }, [caseRef])

  const inboxQuery = useQuery({
    queryKey: ['fusion', 'inbox'],
    queryFn: () => complianceService.listInbox(),
  })

  const casesQuery = useQuery({
    queryKey: ['fusion', 'cases'],
    queryFn: () => complianceService.listCases(),
  })

  const matchedCase = useMemo(
    () => casesQuery.data?.find((c) => c.case_ref === caseRef),
    [casesQuery.data, caseRef]
  )

  const caseId = matchedCase?.id
  const { canExecute } = useFusionPermissions(matchedCase?.investigation_id ?? undefined)
  const mioRefetchInterval = useFusionLiveRefetchInterval(livePaused, Boolean(caseRef))

  const caseQuery = useQuery({
    queryKey: ['fusion', 'case', caseId],
    queryFn: () => complianceService.getCase(caseId!),
    enabled: Boolean(caseId) && queryReady,
    refetchInterval: mioRefetchInterval,
  })

  const graphQuery = useQuery({
    queryKey: ['fusion', 'graph', caseId],
    queryFn: () => complianceService.getGraph(caseId!),
    enabled: Boolean(caseId) && queryReady,
    staleTime: pipelineActive ? 0 : 15_000,
    refetchInterval: pipelineActive ? 1500 : false,
  })

  const riskHistoryQuery = useQuery({
    queryKey: ['fusion', 'risk-history', caseId],
    queryFn: () => complianceService.getCaseRiskHistory(caseId!),
    enabled: Boolean(caseId) && queryReady,
    retry: false,
  })

  const crossLinksQuery = useQuery({
    queryKey: ['fusion', 'cross-links', caseRef],
    queryFn: () => complianceService.getCrossCaseGraphLinks(caseRef),
    enabled: Boolean(caseRef) && queryReady,
    retry: false,
  })

  const timelineQuery = useQuery({
    queryKey: ['fusion', 'timeline', caseRef],
    queryFn: () => complianceService.getCaseTimeline(caseRef),
    enabled: queryReady,
    refetchInterval: pipelineActive ? 2000 : false,
  })

  const workspaceQuery = useQuery({
    queryKey: ['fusion', 'workspace', caseRef],
    queryFn: () => complianceService.getAnalystWorkspaceState({ caseRef }),
    enabled: queryReady,
  })

  const recommendationsQuery = useQuery({
    queryKey: ['fusion', 'recommendations', caseRef],
    queryFn: () => complianceService.getWorkflowRecommendations(caseRef),
    enabled: queryReady,
    refetchInterval: mioRefetchInterval,
  })

  const queueData = useMemo((): FusionQueueRow[] => {
    const inbox = inboxQuery.data ?? []
    return [...inbox].sort((a, b) => {
      const qa = (a as FusionQueueRow & { queue_priority?: number }).queue_priority
      const qb = (b as FusionQueueRow & { queue_priority?: number }).queue_priority
      if (qa != null && qb != null && qa !== qb) return qa - qb
      return 0
    })
  }, [inboxQuery.data])

  const queuePosition = useMemo(() => {
    const idx = queueData.findIndex((r) => r.case_ref === caseRef)
    return idx >= 0 ? idx + 1 : null
  }, [queueData, caseRef])

  const fusionDone = Boolean(
    caseQuery.data?.status === 'fused' ||
      (caseQuery.data?.fusion_result &&
        (Array.isArray((caseQuery.data.fusion_result as Record<string, unknown>).attributions) ||
          Array.isArray((caseQuery.data.fusion_result as Record<string, unknown>).bridges) ||
          Array.isArray((caseQuery.data.fusion_result as Record<string, unknown>).hypotheses)))
  )
  const defaultWallet = useMemo(() => extractDefaultWallet(graphQuery.data), [graphQuery.data])

  const investigationWallet = useMemo(() => {
    const fromSession = caseSession.investigationWallet
    if (fromSession) return fromSession
    const items = caseSession.investigationSeed?.items ?? []
    const w = primaryWallet(items)
    return w ? { address: w.value, chain: w.chain } : undefined
  }, [caseSession])

  const investigationSeedItems = caseSession.investigationSeed?.items ?? []
  const enabledCollectors = caseSession.enabledCollectors ?? []
  const hasRealSeed = Boolean(investigationWallet || investigationSeedItems.length > 0)
  const isDemoCase = Boolean(resolveDemoScenarioId(caseRef) && !hasRealSeed)

  const mioCards = useMemo(() => {
    const lastKyt = caseSession.lastKyt ?? pipelineSession.lastKyt
    const cards = buildMioCards({
      recommendations: recommendationsQuery.data?.recommendations ?? [],
      workflowStatus: caseQuery.data?.workflow_status ?? matchedCase?.workflow_status,
      fusionDone,
      defaultWallet,
      investigationWallet,
      investigationSeed: caseSession.investigationSeed,
      isDemoCase,
      lastKytAddress: lastKyt?.address,
      nodeCountHint: graphQuery.data?.nodes?.length ?? 0,
    })
    return cards.filter((c) => !dismissedCards.includes(c.id))
  }, [
    recommendationsQuery.data,
    caseQuery.data,
    matchedCase,
    fusionDone,
    defaultWallet,
    investigationWallet,
    caseSession.investigationSeed,
    caseSession.lastKyt,
    pipelineSession.lastKyt,
    isDemoCase,
    dismissedCards,
    graphQuery.data?.nodes?.length,
  ])

  useEffect(() => {
    saveLastCaseRef(caseRef)
  }, [caseRef])

  const invalidateCase = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['fusion', 'case', caseId] })
    queryClient.invalidateQueries({ queryKey: ['fusion', 'graph', caseId] })
    queryClient.invalidateQueries({ queryKey: ['fusion', 'recommendations', caseRef] })
    queryClient.invalidateQueries({ queryKey: ['fusion', 'inbox'] })
    queryClient.invalidateQueries({ queryKey: ['fusion', 'timeline', caseRef] })
  }, [queryClient, caseId, caseRef])

  useEffect(() => {
    if (pipelineSession.pipelineStatus !== 'pending') return
    if (pipelineRunningRef.current) return
    pipelineRunningRef.current = true

    void (async () => {
      try {
        const result = await runInvestigationPipeline(caseRef)
        setPipelineTick((n) => n + 1)
        invalidateCase()
        toast.success(
          `${result.caseRef}: ${result.mentions} OSINT · ${result.graphNodes} узлов` +
            (result.screened ? ' · KYT ok' : '')
        )
      } catch (err) {
        mergeCaseSession(caseRef, {
          pipelineStatus: 'error',
          pipelineError: err instanceof Error ? err.message : fusionCopy.investigation.pipelineError,
        })
        setPipelineTick((n) => n + 1)
        toast.error(err instanceof Error ? err.message : fusionCopy.investigation.pipelineError)
      } finally {
        pipelineRunningRef.current = false
      }
    })()
  }, [caseRef, pipelineSession.pipelineStatus, invalidateCase])

  const fuseMutation = useMutation({
    mutationFn: () => complianceService.fuseCase(caseId!, resolveDemoScenarioId(caseRef)),
    onSuccess: () => {
      invalidateCase()
      toast.success(fusionCopy.investigation.fusionComplete)
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const transitionMutation = useMutation({
    mutationFn: (status: string) => complianceService.transitionCase(caseId!, status),
    onSuccess: () => {
      invalidateCase()
      toast.success(fusionCopy.investigation.workflowUpdated)
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const screenMutation = useMutation({
    mutationFn: ({ address, chain }: { address: string; chain?: string }) =>
      complianceService.screenWallet(address, chain),
    onSuccess: (result, vars) => {
      mergeCaseSession(caseRef, {
        lastKyt: {
          address: vars.address,
          chain: vars.chain ?? 'tron',
          score: result.risk_score,
          level: result.risk_level,
          at: Date.now(),
        },
        lastAction: 'screen_wallet',
        lastActionAt: Date.now(),
      })
      setSessionTick((n) => n + 1)
      setDismissedCards((p) => (p.includes('screen_wallet') ? p : [...p, 'screen_wallet']))
      toast.success(fusionCopy.screening(result.risk_score, result.risk_level))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const executeMioCard = useCallback(
    async (card: MioExecutableCard) => {
      if (!caseId) throw new Error('Case not resolved')
      await executeMioCardAction(card, {
        caseId,
        caseRef,
        defaultWallet,
        investigationWallet,
        investigationSeedItems,
        enabledCollectors,
        graphNodes: graphQuery.data?.nodes,
        fuseMutation,
        transitionMutation,
        screenMutation,
        invalidateGraph: invalidateCase,
        openReport: (id) => {
          void openReportUrl(complianceService.reportPdfUrl(id)).catch(() => undefined)
        },
      })
    },
    [
      caseId,
      caseRef,
      defaultWallet,
      investigationWallet,
      investigationSeedItems,
      enabledCollectors,
      graphQuery.data,
      fuseMutation,
      transitionMutation,
      screenMutation,
      invalidateCase,
    ]
  )

  const evidenceItems = workspaceQuery.data?.evidence?.items ?? []

  const investigationSnapshot = useMemo(
    () => ({
      selectedNodeId,
      selectedTimelineEventId,
      selectedEvidenceId,
      replayIndex,
      hopLensMaxDepth,
      dockTab,
      leftTab,
      livePaused,
    }),
    [
      selectedNodeId,
      selectedTimelineEventId,
      selectedEvidenceId,
      replayIndex,
      hopLensMaxDepth,
      dockTab,
      leftTab,
      livePaused,
    ]
  )

  const evolution = useFusionInvestigationEvolution({
    caseRef,
    liveEvents,
    mioCards,
    evidenceItems,
    graph: graphQuery.data,
    snapshot: investigationSnapshot,
  })

  const resolveEvidenceNodeId = useCallback(
    (contentHash: string) => {
      const g = graphQuery.data
      if (!g?.nodes?.length) return null
      const needle = contentHash.slice(0, 12).toLowerCase()
      return (
        g.nodes.find(
          (n) =>
            n.id.toLowerCase().includes(needle) || n.label.toLowerCase().includes(needle)
        )?.id ?? null
      )
    },
    [graphQuery.data]
  )

  const timelineEvents = timelineQuery.data?.events ?? workspaceQuery.data?.timeline?.events ?? []

  const replaySteps = useMemo(
    () => buildReplaySteps(graphQuery.data, timelineEvents),
    [graphQuery.data, timelineEvents]
  )

  const timelineNodeMap = useMemo(
    () => buildTimelineNodeMap(timelineEvents, graphQuery.data),
    [timelineEvents, graphQuery.data]
  )

  const nodeToTimelineEventId = useMemo(() => {
    const reverse = new Map<string, string>()
    timelineNodeMap.forEach((nodeId, eventId) => {
      if (!reverse.has(nodeId)) reverse.set(nodeId, eventId)
    })
    return reverse
  }, [timelineNodeMap])

  useFusionBroadcastSync(
    caseRef,
    { selectedNodeId, replayIndex },
    (remote) => {
      setSelectedNodeId(remote.selectedNodeId)
      setReplayIndex(remote.replayIndex)
      if (remote.selectedNodeId) {
        const eventId = nodeToTimelineEventId.get(remote.selectedNodeId)
        if (eventId) setSelectedTimelineEventId(eventId)
      }
    }
  )

  const handleTimelineEventClick = useCallback(
    (eventId: string) => {
      setSelectedTimelineEventId(eventId)
      const ev = timelineEvents.find((e) => e.id === eventId)
      if (ev && replaySteps.length > 1) {
        setReplayIndex(replayIndexForEvent(ev, replaySteps))
      }
      const nodeId = timelineNodeMap.get(eventId) ?? null
      if (nodeId) setSelectedNodeId(nodeId)
    },
    [timelineNodeMap, timelineEvents, replaySteps]
  )

  const handleGraphNodeSelect = useCallback(
    (nodeId: string | null) => {
      setSelectedNodeId(nodeId)
      if (nodeId) {
        const eventId = nodeToTimelineEventId.get(nodeId) ?? null
        setSelectedTimelineEventId(eventId)
        if (eventId) {
          setLeftTab('timeline')
          requestAnimationFrame(() => {
            timelineItemRefs.current.get(eventId)?.scrollIntoView({
              block: 'nearest',
              behavior: 'smooth',
            })
          })
        }
      } else {
        setSelectedTimelineEventId(null)
      }
    },
    [nodeToTimelineEventId]
  )

  const handleEvidenceDrop = useCallback(
    (contentHash: string, nodeId: string | null) => {
      const item = evidenceItems.find((i) => i.content_hash === contentHash)
      if (item) setSelectedEvidenceId(item.id)
      if (nodeId) handleGraphNodeSelect(nodeId)
      else {
        const resolved = resolveEvidenceNodeId(contentHash)
        if (resolved) handleGraphNodeSelect(resolved)
      }
      toast.success(fusionCopy.investigation.evidenceLinked)
    },
    [evidenceItems, resolveEvidenceNodeId, handleGraphNodeSelect]
  )

  const handleEvidenceClick = useCallback(
    (itemId: string, contentHash: string) => {
      setSelectedEvidenceId(itemId)
      const nodeId = resolveEvidenceNodeId(contentHash)
      if (nodeId) handleGraphNodeSelect(nodeId)
    },
    [resolveEvidenceNodeId, handleGraphNodeSelect]
  )

  useEffect(() => {
    if (!selectedTimelineEventId) return
    timelineItemRefs.current.get(selectedTimelineEventId)?.scrollIntoView({
      block: 'nearest',
      behavior: 'smooth',
    })
  }, [selectedTimelineEventId, leftTab])

  useEffect(() => {
    if (replaySteps.length <= 1) return
    const eventId = eventIdAtReplayIndex(timelineEvents, replayIndex, replaySteps)
    if (eventId && eventId !== selectedTimelineEventId) {
      setSelectedTimelineEventId(eventId)
    }
  }, [replayIndex, replaySteps, timelineEvents, selectedTimelineEventId])

  const highlightNodeIds = useMemo(() => {
    if (replaySteps.length > 1) {
      const cumulative = cumulativeReplayHighlights(
        timelineEvents,
        timelineNodeMap,
        replayIndex,
        replaySteps
      )
      if (cumulative.length) return cumulative
    }
    if (!selectedTimelineEventId) return selectedNodeId ? [selectedNodeId] : []
    const nodeId = timelineNodeMap.get(selectedTimelineEventId)
    return nodeId ? [nodeId] : selectedNodeId ? [selectedNodeId] : []
  }, [
    replaySteps,
    replayIndex,
    timelineEvents,
    timelineNodeMap,
    selectedTimelineEventId,
    selectedNodeId,
  ])

  const fusion = caseQuery.data?.fusion_result as Record<string, unknown> | null | undefined
  const hypotheses = Array.isArray(fusion?.hypotheses)
    ? (fusion.hypotheses as Array<{ statement_ru?: string; confidence?: number }>)
    : []

  const riskPoints = riskHistoryQuery.data?.points ?? []
  const latestRisk = riskPoints.length ? riskPoints[riskPoints.length - 1] : null

  const graphDetachUrl =
    typeof window !== 'undefined'
      ? `${window.location.origin}/dashboard/fusion/investigation/${encodeURIComponent(caseRef)}/graph`
      : undefined

  const handleExecAll = useCallback(async () => {
    if (!canExecute) {
      toast.error(fusionCopy.mio.viewerBlocked)
      return
    }
    if (!mioCards.length) return
    batchCancelRef.current = false
    setBatchRunning(true)
    setBatchProgress({ current: 0, total: mioCards.length })
    try {
      const result = await runMioBatch(
        mioCards,
        executeMioCard,
        (p) => setBatchProgress({ current: p.current, total: p.total }),
        { shouldCancel: () => batchCancelRef.current }
      )
      const cancelled = result.failed.some((f) => f.cardId === '__cancelled__')
      const realFails = result.failed.filter((f) => f.cardId !== '__cancelled__')
      if (cancelled) {
        toast.message(fusionCopy.mio.batchCancelled)
      } else if (realFails.length && result.succeeded.length) {
        toast.warning(fusionCopy.mio.batchPartial(result.succeeded.length, realFails.length))
      } else if (realFails.length) {
        toast.error(fusionCopy.mio.batchFailed(realFails.length))
      } else {
        toast.success(fusionCopy.mio.batchComplete)
      }
      invalidateCase()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : fusionCopy.mio.batchError)
    } finally {
      setBatchRunning(false)
      setBatchProgress(null)
      batchCancelRef.current = false
    }
  }, [canExecute, mioCards, executeMioCard, invalidateCase])

  const cancelBatch = useCallback(() => {
    batchCancelRef.current = true
  }, [])

  const retryPipeline = useCallback(() => {
    const session = loadCaseSession(caseRef)
    const hasSeed = (session.investigationSeed?.items?.length ?? 0) > 0
    if (!hasSeed) {
      setActiveLensState('collect')
      navigate({
        to: '/dashboard/fusion/investigation/$caseRef',
        params: { caseRef },
        search: fusionMissionSearch('collect'),
        replace: true,
      })
      toast.info(fusionCopy.investigation.seedRequired)
      return
    }
    retryInvestigationPipeline(caseRef)
    setPipelineTick((n) => n + 1)
  }, [caseRef, navigate])

  const livePulse =
    graphAlerts.length > 0
      ? fusionCopy.graph.graphAlerts(graphAlerts.length)
      : liveEvents[0]?.text_ru ?? liveEvents[0]?.type ?? null

  const refreshSession = useCallback(() => setSessionTick((n) => n + 1), [])

  return {
    caseRef,
    caseId,
    liveEvents,
    graphAlerts,
    leftTab,
    setLeftTab,
    dockTab,
    setDockTab,
    activeLens,
    setActiveLens,
    contextCollapsed,
    setContextCollapsed,
    selectedNodeId,
    setSelectedNodeId,
    selectedTimelineEventId,
    selectedEvidenceId,
    replayIndex,
    setReplayIndex,
    hopLensMaxDepth,
    setHopLensMaxDepth,
    livePaused,
    batchRunning,
    canExecute,
    fusionDone,
    mioCards,
    setDismissedCards,
    graphQuery,
    caseQuery,
    workspaceQuery,
    crossLinksQuery,
    matchedCase,
    latestRisk,
    queuePosition,
    queueData,
    timelineEvents,
    timelineNodeMap,
    evidenceItems,
    hypotheses,
    replaySteps,
    highlightNodeIds,
    evolution,
    graphDetachUrl,
    fusion,
    graphContainerRef,
    timelineItemRefs,
    handleTimelineEventClick,
    handleGraphNodeSelect,
    handleEvidenceDrop,
    handleEvidenceClick,
    resolveEvidenceNodeId,
    executeMioCard,
    handleExecAll,
    cancelBatch,
    batchProgress,
    livePulse,
    screenMutation,
    fuseMutation,
    refreshSession,
    retryPipeline,
    hasRealSeed,
    pipelineActive,
    pipelinePhase,
    pipelineError: pipelineSession.pipelineStatus === 'error',
    pipelineErrorMessage: pipelineSession.pipelineError ?? null,
    pipelineCollectorStatus: pipelineSession.pipelineCollectorStatus,
    pipelineCollectorsRun: pipelineSession.pipelineCollectorsRun,
    lastKyt: pipelineSession.lastKyt ?? caseSession.lastKyt,
  }
}

export type InvestigationWorkspace = ReturnType<typeof useInvestigationWorkspace>
