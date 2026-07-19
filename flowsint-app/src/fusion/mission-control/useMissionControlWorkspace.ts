import { useCallback, useEffect, useMemo, useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useNavigate } from '@tanstack/react-router'

import { complianceService } from '@/api/compliance-service'

import { useComplianceEvents } from '@/hooks/use-compliance-events'

import { useFusionPermissions } from '@/hooks/use-fusion-permissions'

import { subscribeFusionSync } from '@/fusion/fusion-sync-bus'

import { useFusionLiveRefetchInterval, runMioBatch } from '@/fusion/fusion-mio-batch'

import { buildReplaySteps } from '@/fusion/fusion-graph-utils'

import {
  buildMioCards,
  extractDefaultWallet,
  type MioExecutableCard,
} from '@/fusion/fusion-mio-actions'

import { resolveDemoScenarioId } from '@/fusion/fusion-demo-scenarios'

import { executeMioCardAction } from '@/fusion/fusion-mio-execute'

import { openReportUrl } from '@/fusion/reports/report-api'

import { loadCaseSession, mergeCaseSession } from '@/fusion/fusion-case-session'

import { primaryWallet } from '@/fusion/fusion-investigation-seed'

import type { GraphDiffEvent } from '@/fusion/fusion-graph-diff'

import { useFusionIntelligenceStream } from '@/fusion/useFusionIntelligenceStream'

import type { FusionOpsLens } from '@/fusion/FusionRail'

import type { FusionQueueRow } from '@/fusion/FusionQueuePanel'

import { fusionMissionSearch } from '@/fusion/fusion-route-search'

import { fusionCopy } from '@/fusion/fusion-copy'

import { resolveInvestigationPhase } from '@/fusion/fusion-investigation-phase'

import { toast } from 'sonner'

function lensFromSearch(lens?: FusionOpsLens): FusionOpsLens {
  if (lens === 'queue' || lens === 'collect' || lens === 'brief') return lens
  return 'canvas'
}

const MC_PREVIEW_KEY = 'finskalp-mc-preview-ref'

function readStoredPreviewRef(): string | null {
  try {
    return sessionStorage.getItem(MC_PREVIEW_KEY)
  } catch {
    return null
  }
}

function writeStoredPreviewRef(ref: string | null) {
  try {
    if (ref) sessionStorage.setItem(MC_PREVIEW_KEY, ref)
    else sessionStorage.removeItem(MC_PREVIEW_KEY)
  } catch {
    /* ignore */
  }
}

type InboxRow = Awaited<ReturnType<typeof complianceService.listInbox>>[number]

export function useMissionControlWorkspace(lensSearch?: FusionOpsLens) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { liveEvents, graphAlerts } = useComplianceEvents({ enabled: true })
  const [dismissedCards, setDismissedCards] = useState<string[]>([])
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null)
  const [dockTab, setDockTab] = useState('timeline')
  const [livePaused, setLivePausedState] = useState(false)
  const [graphDiffEvents, setGraphDiffEvents] = useState<GraphDiffEvent[]>([])
  const [activeLens, setActiveLensState] = useState<FusionOpsLens>(() => lensFromSearch(lensSearch))
  const [batchRunning, setBatchRunning] = useState(false)
  const [replayIndex, setReplayIndex] = useState(0)
  const [sessionTick, setSessionTick] = useState(0)
  const [previewCaseRefOverride, setPreviewCaseRefOverride] = useState<string | null>(() =>
    readStoredPreviewRef()
  )

  useEffect(() => {
    setActiveLensState(lensFromSearch(lensSearch))
  }, [lensSearch])

  const setActiveLens = useCallback(
    (next: FusionOpsLens) => {
      setActiveLensState(next)
      const nextSearch = fusionMissionSearch(next === 'canvas' ? undefined : next)
      navigate({ to: '/dashboard/fusion', search: nextSearch, replace: true })
    },
    [navigate]
  )

  useEffect(() => {
    return subscribeFusionSync((sync) => {
      if (sync.activeDockTab) setDockTab(sync.activeDockTab)
      setLivePausedState(sync.livePaused)
    })
  }, [])

  const inboxQuery = useQuery({
    queryKey: ['fusion', 'inbox'],
    queryFn: () => complianceService.listInbox(),
    refetchInterval: 30_000,
    staleTime: 30_000,
  })

  const statsQuery = useQuery({
    queryKey: ['fusion', 'workflow-stats'],
    queryFn: () => complianceService.getWorkflowStats(),
    refetchInterval: 30_000,
  })
  const workflowStats = statsQuery.data

  const previewRow = useMemo(() => {
    const inbox = inboxQuery.data ?? []
    if (!inbox.length) return undefined
    if (previewCaseRefOverride) {
      const hit = inbox.find((r) => (r.case_ref ?? r.case_id) === previewCaseRefOverride)
      if (hit) return hit
    }
    return inbox[0]
  }, [inboxQuery.data, previewCaseRefOverride])

  useEffect(() => {
    if (!inboxQuery.data?.length) return
    if (
      previewCaseRefOverride &&
      inboxQuery.data.some((r) => (r.case_ref ?? r.case_id) === previewCaseRefOverride)
    ) {
      return
    }
    const firstRef = inboxQuery.data[0].case_ref ?? inboxQuery.data[0].case_id
    setPreviewCaseRefOverride(firstRef)
    writeStoredPreviewRef(firstRef)
  }, [inboxQuery.data, previewCaseRefOverride])

  const previewCaseId = previewRow?.case_id
  const previewCaseRef = previewRow?.case_ref ?? previewRow?.case_id ?? null

  const setPreviewCase = useCallback((ref: string) => {
    setPreviewCaseRefOverride(ref)
    writeStoredPreviewRef(ref)
    setSelectedNodeId(null)
    setSelectedEvidenceId(null)
    setGraphDiffEvents([])
  }, [])

  const onGraphDiff = useCallback((events: GraphDiffEvent[]) => {
    setGraphDiffEvents((prev) => [...events, ...prev].slice(0, 40))
  }, [])

  useEffect(() => {
    setGraphDiffEvents([])
  }, [previewCaseRef])

  const mioRefetchInterval = useFusionLiveRefetchInterval(livePaused, Boolean(previewCaseRef))

  const previewCaseQuery = useQuery({
    queryKey: ['fusion', 'preview-case', previewCaseId],
    queryFn: () => complianceService.getCase(previewCaseId!),
    enabled: Boolean(previewCaseId),
    refetchInterval: mioRefetchInterval,
  })

  const graphQuery = useQuery({
    queryKey: ['fusion', 'preview-graph', previewCaseId],
    queryFn: () => complianceService.getGraph(previewCaseId!),
    enabled: Boolean(previewCaseId),
  })

  const riskHistoryQuery = useQuery({
    queryKey: ['fusion', 'preview-risk', previewCaseId],
    queryFn: () => complianceService.getCaseRiskHistory(previewCaseId!),
    enabled: Boolean(previewCaseId),
    retry: false,
  })
  const latestRisk = riskHistoryQuery.data?.points?.slice(-1)[0]

  const recommendationsQuery = useQuery({
    queryKey: ['fusion', 'preview-recs', previewCaseRef],
    queryFn: () => complianceService.getWorkflowRecommendations(previewCaseRef!),
    enabled: Boolean(previewCaseRef),
    retry: false,
    refetchInterval: mioRefetchInterval,
  })

  const timelineQuery = useQuery({
    queryKey: ['fusion', 'preview-timeline', previewCaseRef],
    queryFn: () => complianceService.getCaseTimeline(previewCaseRef!),
    enabled: Boolean(previewCaseRef),
    retry: false,
  })

  const workspaceQuery = useQuery({
    queryKey: ['fusion', 'preview-workspace', previewCaseRef],
    queryFn: () => complianceService.getAnalystWorkspaceState({ caseRef: previewCaseRef! }),
    enabled: Boolean(previewCaseRef),
    retry: false,
  })

  const fuseMutation = useMutation({
    mutationFn: () =>
      complianceService.fuseCase(previewCaseId!, resolveDemoScenarioId(previewCaseRef)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fusion', 'preview-case', previewCaseId] })
      queryClient.invalidateQueries({ queryKey: ['fusion', 'preview-graph', previewCaseId] })
      setDockTab('reports')
      toast.success(fusionCopy.investigation.fusionComplete)
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const transitionMutation = useMutation({
    mutationFn: (status: string) => complianceService.transitionCase(previewCaseId!, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fusion', 'preview-case', previewCaseId] })
      queryClient.invalidateQueries({ queryKey: ['fusion', 'inbox'] })
      toast.success(fusionCopy.investigation.workflowUpdated)
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const screenMutation = useMutation({
    mutationFn: ({ address, chain }: { address: string; chain?: string }) =>
      complianceService.screenWallet(address, chain),
    onSuccess: (result, vars) => {
      if (previewCaseRef) {
        mergeCaseSession(previewCaseRef, {
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
      }
      toast.success(fusionCopy.screening(result.risk_score, result.risk_level))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const queueData = useMemo((): FusionQueueRow[] => {
    const inbox = inboxQuery.data ?? []
    return [...inbox].sort((a, b) => {
      const qa = (a as InboxRow & { queue_priority?: number }).queue_priority
      const qb = (b as InboxRow & { queue_priority?: number }).queue_priority
      if (qa != null && qb != null && qa !== qb) return qa - qb
      return 0
    })
  }, [inboxQuery.data])

  const criticalCaseCount = useMemo(
    () => queueData.filter((r) => r.priority?.toLowerCase() === 'critical').length,
    [queueData]
  )

  const slaBreachCount = useMemo(
    () => workflowStats?.sla_breached ?? queueData.filter((r) => r.sla_breached).length,
    [workflowStats, queueData]
  )

  const fusionDone = Boolean(
    previewCaseQuery.data?.status === 'fused' ||
      (previewCaseQuery.data?.fusion_result &&
        (Array.isArray((previewCaseQuery.data.fusion_result as Record<string, unknown>).attributions) ||
          Array.isArray((previewCaseQuery.data.fusion_result as Record<string, unknown>).bridges) ||
          Array.isArray((previewCaseQuery.data.fusion_result as Record<string, unknown>).hypotheses)))
  )
  const defaultWallet = useMemo(() => extractDefaultWallet(graphQuery.data), [graphQuery.data])
  const previewSession = useMemo(() => {
    void sessionTick
    return previewCaseRef ? loadCaseSession(previewCaseRef) : {}
  }, [previewCaseRef, sessionTick])
  const investigationWallet = useMemo(() => {
    const fromSession = previewSession.investigationWallet
    if (fromSession) return fromSession
    const items = previewSession.investigationSeed?.items ?? []
    const w = primaryWallet(items)
    if (w) return { address: w.value, chain: w.chain }
    return defaultWallet ?? undefined
  }, [previewSession, defaultWallet])
  const investigationSeedItems = previewSession.investigationSeed?.items ?? []
  const enabledCollectors = previewSession.enabledCollectors ?? []
  const hasRealSeed = Boolean(investigationWallet || investigationSeedItems.length > 0)
  const isDemoCase = Boolean(previewCaseRef && resolveDemoScenarioId(previewCaseRef) && !hasRealSeed)
  const nodeCount = graphQuery.data?.nodes?.length ?? 0
  const lastKyt = previewSession.lastKyt

  const mioCards = useMemo(() => {
    const cards = buildMioCards({
      recommendations: recommendationsQuery.data?.recommendations ?? [],
      workflowStatus: previewCaseQuery.data?.workflow_status,
      fusionDone,
      defaultWallet,
      investigationWallet,
      investigationSeed: previewSession.investigationSeed,
      isDemoCase,
      lastKytAddress: lastKyt?.address,
      nodeCountHint: nodeCount,
    })
    return cards.filter((c) => !dismissedCards.includes(c.id))
  }, [
    recommendationsQuery.data,
    previewCaseQuery.data,
    fusionDone,
    defaultWallet,
    investigationWallet,
    previewSession.investigationSeed,
    lastKyt?.address,
    isDemoCase,
    dismissedCards,
    nodeCount,
  ])

  const phaseSnap = useMemo(
    () =>
      resolveInvestigationPhase({
        hasSeed: hasRealSeed || nodeCount > 0,
        nodeCount,
        pipelineActive: false,
        pipelineError: false,
        kytDone: Boolean(lastKyt?.address),
        kytApplicable: nodeCount > 0 || Boolean(investigationWallet),
        fusionDone,
      }),
    [hasRealSeed, nodeCount, lastKyt?.address, investigationWallet, fusionDone]
  )

  const executeMioCard = useCallback(
    async (card: MioExecutableCard) => {
      if (!previewCaseId) {
        throw new Error(fusionCopy.missionControl.caseNotSelected)
      }
      await executeMioCardAction(card, {
        caseId: previewCaseId,
        caseRef: previewCaseRef,
        defaultWallet,
        investigationWallet,
        investigationSeedItems,
        enabledCollectors,
        graphNodes: graphQuery.data?.nodes,
        fuseMutation,
        transitionMutation,
        screenMutation,
        invalidateGraph: () => {
          queryClient.invalidateQueries({ queryKey: ['fusion', 'preview-graph', previewCaseId] })
          queryClient.invalidateQueries({ queryKey: ['fusion', 'preview-case', previewCaseId] })
        },
        openReport: (caseId) => {
          void openReportUrl(complianceService.reportPdfUrl(caseId)).catch(() => undefined)
        },
      })
    },
    [
      previewCaseId,
      previewCaseRef,
      defaultWallet,
      investigationWallet,
      investigationSeedItems,
      enabledCollectors,
      graphQuery.data,
      fuseMutation,
      transitionMutation,
      screenMutation,
      queryClient,
    ]
  )

  const { canExecute } = useFusionPermissions()

  const timelineEvents = timelineQuery.data?.events ?? workspaceQuery.data?.timeline?.events ?? []
  const evidenceItems = workspaceQuery.data?.evidence?.items ?? []

  useFusionIntelligenceStream({
    caseRef: previewCaseRef,
    liveEvents,
    mioCards,
    graphDiffEvents,
    evidenceItems,
    enabled: Boolean(previewCaseRef),
  })

  const fusion = previewCaseQuery.data?.fusion_result as Record<string, unknown> | null | undefined

  const resolveEvidenceNodeId = useCallback(
    (contentHash: string) => {
      const graph = graphQuery.data
      if (!graph?.nodes?.length) return null
      const needle = contentHash.slice(0, 12).toLowerCase()
      return (
        graph.nodes.find(
          (n) =>
            n.id.toLowerCase().includes(needle) || n.label.toLowerCase().includes(needle)
        )?.id ?? null
      )
    },
    [graphQuery.data]
  )

  const handleEvidenceDrop = useCallback(
    (contentHash: string, nodeId: string | null) => {
      const item = evidenceItems.find((i) => i.content_hash === contentHash)
      if (item) setSelectedEvidenceId(item.id)
      if (nodeId) setSelectedNodeId(nodeId)
      else {
        const resolved = resolveEvidenceNodeId(contentHash)
        if (resolved) setSelectedNodeId(resolved)
      }
      toast.success(fusionCopy.investigation.evidenceLinked)
    },
    [evidenceItems, resolveEvidenceNodeId]
  )

  const handleEvidenceClick = useCallback(
    (itemId: string, contentHash: string) => {
      setSelectedEvidenceId(itemId)
      const nodeId = resolveEvidenceNodeId(contentHash)
      if (nodeId) setSelectedNodeId(nodeId)
    },
    [resolveEvidenceNodeId]
  )

  const replaySteps = useMemo(
    () => buildReplaySteps(graphQuery.data, timelineEvents),
    [graphQuery.data, timelineEvents]
  )

  const handleExecAll = useCallback(async () => {
    if (!canExecute) {
      toast.error(fusionCopy.mio.viewerBlocked)
      return
    }
    if (!mioCards.length) return
    setBatchRunning(true)
    try {
      const result = await runMioBatch(mioCards, executeMioCard)
      if (result.failed.length) {
        toast.error(fusionCopy.mio.batchFailed(result.failed.length))
      } else {
        toast.success(fusionCopy.mio.batchComplete)
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : fusionCopy.mio.batchError)
    } finally {
      setBatchRunning(false)
    }
  }, [canExecute, mioCards, executeMioCard])

  const handleExecuteCard = useCallback(
    async (card: MioExecutableCard) => {
      if (!canExecute) {
        toast.error(fusionCopy.mio.viewerBlocked)
        return
      }
      try {
        await executeMioCard(card)
        if (card.actionKind === 'fuse') {
          toast.success(fusionCopy.investigation.fusionComplete)
          setDockTab('reports')
        }
      } catch (e) {
        toast.error(e instanceof Error ? e.message : fusionCopy.mio.batchError)
      }
    },
    [canExecute, executeMioCard]
  )

  const handleStageNext = useCallback(async () => {
    if (!previewCaseRef) {
      setActiveLens('collect')
      return
    }
    switch (phaseSnap.nextActionKind) {
      case 'collect':
        void navigate({
          to: '/dashboard/fusion/investigation/$caseRef',
          params: { caseRef: previewCaseRef },
          search: fusionMissionSearch('collect'),
        })
        return
      case 'kyt': {
        const card = mioCards.find((c) => c.actionKind === 'screen_wallet')
        if (card) {
          await handleExecuteCard(card)
          return
        }
        if (investigationWallet) {
          screenMutation.mutate({
            address: investigationWallet.address,
            chain: investigationWallet.chain,
          })
          return
        }
        toast.error('Нет адреса для KYT')
        return
      }
      case 'fuse':
        if (!previewCaseId) {
          toast.error(fusionCopy.missionControl.caseNotSelected)
          return
        }
        fuseMutation.mutate()
        setDockTab('reports')
        return
      case 'reports':
        void navigate({
          to: '/dashboard/fusion/reports/$caseRef',
          params: { caseRef: previewCaseRef },
        })
        return
      default:
        void navigate({
          to: '/dashboard/fusion/investigation/$caseRef',
          params: { caseRef: previewCaseRef },
        })
    }
  }, [
    previewCaseRef,
    previewCaseId,
    phaseSnap.nextActionKind,
    mioCards,
    handleExecuteCard,
    investigationWallet,
    screenMutation,
    fuseMutation,
    navigate,
    setActiveLens,
  ])

  const livePulse =
    graphAlerts.length > 0
      ? fusionCopy.graph.graphAlerts(graphAlerts.length)
      : liveEvents[0]?.text_ru ?? liveEvents[0]?.type ?? null

  const latestSseEvent = liveEvents[0]?.text_ru ?? liveEvents[0]?.type ?? null

  return {
    activeLens,
    setActiveLens,
    previewCaseId,
    previewCaseRef,
    previewCaseQuery,
    graphQuery,
    workspaceQuery,
    queueData,
    workflowStats,
    criticalCaseCount,
    slaBreachCount,
    latestSseEvent,
    fusionDone,
    phaseSnap,
    handleStageNext,
    fuseMutation,
    screenMutation,
    fusion,
    latestRisk,
    liveEvents,
    graphAlerts,
    livePaused,
    mioCards,
    canExecute,
    batchRunning,
    dockTab,
    setDockTab,
    selectedNodeId,
    setSelectedNodeId,
    selectedEvidenceId,
    timelineEvents,
    evidenceItems,
    replaySteps,
    replayIndex,
    setReplayIndex,
    onGraphDiff,
    handleEvidenceDrop,
    handleEvidenceClick,
    resolveEvidenceNodeId,
    handleExecAll,
    handleExecuteCard,
    executeMioCard,
    setDismissedCards,
    setPreviewCase,
    livePulse,
  }
}

export type MissionControlWorkspace = ReturnType<typeof useMissionControlWorkspace>
