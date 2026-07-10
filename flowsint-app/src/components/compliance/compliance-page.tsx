import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  complianceService,
  type ComplianceCase,
  type ComplianceCaseListItem,
  type EvidenceGraph,
} from '@/api/compliance-service'
import { PageLayout } from '@/components/layout/page-layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { Skeleton } from '@/components/ui/skeleton'
import {
  demoEntities,
  demoEvidence,
  EnterpriseContextBar,
  EnterprisePageHero,
  EnterprisePanel,
  EntityCard,
  EvidenceRow,
  ExplainabilityDrawer,
  RiskBadge,
} from '@/components/enterprise/enterprise-ui'

const WORKFLOW_COLUMNS = [
  { id: 'new', label: 'Intake' },
  { id: 'triage', label: 'Triage' },
  { id: 'investigating', label: 'Investigating' },
  { id: 'pending_filing', label: 'Pending filing' },
  { id: 'filed', label: 'Filed' },
  { id: 'archived', label: 'Archived' },
] as const

const WORKFLOW_NEXT: Record<string, string | undefined> = {
  new: 'triage',
  triage: 'investigating',
  investigating: 'pending_filing',
  pending_filing: 'filed',
  filed: 'archived',
}

function graphToFlow(graph?: EvidenceGraph | null): { nodes: Node[]; edges: Edge[] } {
  if (!graph?.nodes?.length) {
    return { nodes: [], edges: [] }
  }

  const nodes: Node[] = graph.nodes.map((node, index) => ({
    id: node.id,
    position: { x: (index % 4) * 220, y: Math.floor(index / 4) * 120 },
    data: { label: `${node.label}\n${node.kind}` },
    style: {
      border: '1px solid var(--fs-border)',
      borderRadius: 6,
      padding: 10,
      background: 'var(--fs-surface)',
      color: 'var(--fs-text-primary)',
      fontSize: 12,
      width: 190,
    },
  }))

  const edges: Edge[] = graph.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.rel_type,
    animated: (edge.strength ?? 0) >= 0.7,
  }))

  return { nodes, edges }
}

function CompliancePageInner() {
  const [caseRef, setCaseRef] = useState(`CASE-${Date.now()}`)
  const [wallet, setWallet] = useState('TRU_HUB_MSK')
  const [scenarioId, setScenarioId] = useState('p2p_rub_offshore')
  const [activeCase, setActiveCase] = useState<ComplianceCase | null>(null)
  const [kgEntityId, setKgEntityId] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)

  const graphQuery = useQuery({
    queryKey: ['compliance', 'graph', activeCase?.id],
    queryFn: () => complianceService.getGraph(activeCase!.id),
    enabled: Boolean(activeCase?.id && activeCase.status !== 'draft'),
  })

  const casesQuery = useQuery({
    queryKey: ['compliance', 'cases'],
    queryFn: () => complianceService.listCases(),
    refetchInterval: 30_000,
  })

  const workflowStatsQuery = useQuery({
    queryKey: ['compliance', 'workflow-stats'],
    queryFn: () => complianceService.getWorkflowStats(),
  })

  const kgModelQuery = useQuery({
    queryKey: ['compliance', 'kg-model'],
    queryFn: () => complianceService.getKnowledgeModel(),
  })

  const kgEntityQuery = useQuery({
    queryKey: ['compliance', 'kg-entity', kgEntityId],
    queryFn: () => complianceService.getKgEntity(kgEntityId.trim()),
    enabled: kgEntityId.trim().length >= 8,
  })

  const kgNeighborsQuery = useQuery({
    queryKey: ['compliance', 'kg-neighbors', kgEntityId],
    queryFn: () => complianceService.getKgEntityNeighbors(kgEntityId.trim()),
    enabled: Boolean(kgEntityQuery.data?.entity),
  })

  const connectorsManifestQuery = useQuery({
    queryKey: ['compliance', 'connectors-manifest'],
    queryFn: () => complianceService.getConnectorsManifest(),
  })

  const intelligenceManifestQuery = useQuery({
    queryKey: ['compliance', 'intelligence-manifest'],
    queryFn: () => complianceService.getIntelligenceManifest(),
  })

  const designSystemManifestQuery = useQuery({
    queryKey: ['compliance', 'design-system-manifest'],
    queryFn: () => complianceService.getDesignSystemManifest(),
  })

  const workspaceQuery = useQuery({
    queryKey: ['compliance', 'investigation-workspace', activeCase?.case_ref],
    queryFn: () => complianceService.getInvestigationWorkspace(activeCase!.case_ref),
    enabled: Boolean(activeCase?.case_ref),
  })

  const transitionMutation = useMutation({
    mutationFn: ({ caseId, status }: { caseId: string; status: string }) =>
      complianceService.transitionCase(caseId, status),
    onSuccess: () => {
      casesQuery.refetch()
      workflowStatsQuery.refetch()
      toast.success('Case status updated')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const createMutation = useMutation({
    mutationFn: () => complianceService.createCase(caseRef),
    onSuccess: (created) => {
      setActiveCase(created)
      toast.success(`Case ${created.case_ref} created`)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const fuseMutation = useMutation({
    mutationFn: () => complianceService.fuseCase(activeCase!.id, scenarioId),
    onSuccess: async () => {
      const refreshed = await complianceService.getCase(activeCase!.id)
      setActiveCase(refreshed)
      graphQuery.refetch()
      toast.success('OSINT Fusion completed')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const screenMutation = useMutation({
    mutationFn: () => complianceService.screenWallet(wallet),
    onSuccess: (result: Record<string, unknown>) => {
      toast.success(`Screening ${result.risk_score}/100 (${result.risk_level})`)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const intelligenceMutation = useMutation({
    mutationFn: () =>
      complianceService.runIntelligenceAnalysis({
        address: wallet,
        chain: 'tron',
        case_ref: activeCase?.case_ref,
        publish: true,
      }),
    onSuccess: (result) => {
      toast.success(`Analysis ${result.aggregate_risk_score.toFixed(1)}/100 · ${result.risk_level}`)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const flow = useMemo(() => graphToFlow(graphQuery.data), [graphQuery.data])
  const riskMeta = (activeCase?.fusion_result as Record<string, any> | undefined)?.metrics
    ?.risk_scoring as Record<string, any> | undefined

  const casesByWorkflow = useMemo(() => {
    const map: Record<string, ComplianceCaseListItem[]> = Object.fromEntries(
      WORKFLOW_COLUMNS.map((column) => [column.id, []])
    )
    for (const item of casesQuery.data ?? []) {
      const state = item.workflow_status || 'new'
      ;(map[state] ?? map.new).push(item)
    }
    return map
  }, [casesQuery.data])

  const activeRisk = riskMeta?.xgboost?.blended_score
    ? riskMeta.xgboost.blended_score >= 80
      ? 'critical'
      : riskMeta.xgboost.blended_score >= 60
        ? 'high'
        : riskMeta.xgboost.blended_score >= 35
          ? 'medium'
          : 'low'
    : 'medium'

  return (
    <PageLayout
      title="Compliance Case Lifecycle"
      description="Investigation-first lifecycle management, API integration status, explainable risk, and knowledge graph exploration."
    >
      <EnterprisePageHero
        eyebrow="compliance-case-lifecycle"
        title="Compliance Case Lifecycle"
        description="Sovereign intake, explainable risk scoring, graph exploration, and filing operations aligned to RFC-0008."
        actions={
          <>
            <Button size="sm" className="rounded-sm" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              Create case
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="rounded-sm border-[var(--fs-border)]"
              onClick={() => fuseMutation.mutate()}
              disabled={!activeCase || fuseMutation.isPending}
            >
              Run fusion
            </Button>
          </>
        }
        metrics={[
          { label: 'Open cases', value: String(casesQuery.data?.length ?? 0) },
          { label: 'SLA breach', value: String(workflowStatsQuery.data?.sla_breached ?? 0), tone: 'critical' },
          { label: 'Connectors', value: String(connectorsManifestQuery.data?.total ?? 0), tone: 'accent' },
          { label: 'Workspace evidence', value: String(workspaceQuery.data?.evidence_count ?? 0) },
        ]}
      />

      {activeCase ? (
        <EnterpriseContextBar
          caseId={activeCase.case_ref}
          status={activeCase.status}
          priority={String(activeCase.priority ?? 'normal')}
          owner="Compliance desk"
          risk={activeRisk}
          objectCount={String(graphQuery.data?.nodes?.length ?? 0)}
          evidenceCount={String(workspaceQuery.data?.evidence_count ?? 0)}
        />
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.85fr]">
        <div className="space-y-6">
          <EnterprisePanel
            title="Intake And Screening"
            description="Create compliance cases, run wallet checks, and preserve a single active investigation context."
          >
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-3">
                <Input value={caseRef} onChange={(e) => setCaseRef(e.target.value)} placeholder="CASE-2026-001" />
                <Input value={scenarioId} onChange={(e) => setScenarioId(e.target.value)} placeholder="p2p_rub_offshore" />
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
                    Create case
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => fuseMutation.mutate()} disabled={!activeCase || fuseMutation.isPending}>
                    OSINT fusion
                  </Button>
                  {activeCase?.fusion_result ? (
                    <Button size="sm" variant="outline" asChild>
                      <a href={complianceService.reportPdfUrl(activeCase.id)} target="_blank" rel="noreferrer">
                        Report PDF
                      </a>
                    </Button>
                  ) : null}
                </div>
              </div>
              <div className="space-y-3">
                <Input value={wallet} onChange={(e) => setWallet(e.target.value)} placeholder="TRON / ETH / BTC address" />
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" onClick={() => screenMutation.mutate()} disabled={!wallet || screenMutation.isPending}>
                    Screen wallet
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => intelligenceMutation.mutate()} disabled={!wallet || intelligenceMutation.isPending}>
                    Run analysis
                  </Button>
                </div>
                <p className="text-xs text-[var(--fs-text-secondary)]">
                  Entity-first scoring combines registry, OSINT, and blockchain evidence before any filing recommendation is shown.
                </p>
              </div>
            </div>
          </EnterprisePanel>

          <EnterprisePanel
            title="Regulatory Reporting"
            description="Case queue, filing readiness, and analyst-controlled transition workflow."
          >
            {casesQuery.isLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : (
              <div className="grid gap-3 lg:grid-cols-3 xl:grid-cols-6">
                {WORKFLOW_COLUMNS.map((column) => (
                  <div
                    key={column.id}
                    className="rounded-md border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] p-3"
                  >
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--fs-text-tertiary)]">
                        {column.label}
                      </p>
                      <Badge className="rounded-sm border border-[var(--fs-border)] bg-transparent text-[var(--fs-text-secondary)]">
                        {casesByWorkflow[column.id]?.length ?? 0}
                      </Badge>
                    </div>
                    <div className="space-y-2">
                      {(casesByWorkflow[column.id] ?? []).slice(0, 4).map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          onClick={async () => setActiveCase(await complianceService.getCase(item.id))}
                          className="w-full rounded-sm border border-[var(--fs-border)] bg-[var(--fs-surface)] p-3 text-left"
                        >
                          <p className="font-mono text-xs text-[var(--fs-accent)]">{item.case_ref}</p>
                          <p className="mt-1 text-sm text-[var(--fs-text-primary)]">{item.priority ?? 'normal'}</p>
                          <div className="mt-2 flex items-center justify-between">
                            <span className="text-xs text-[var(--fs-text-secondary)]">
                              {item.sla_breached ? 'SLA breach' : 'Within SLA'}
                            </span>
                            {WORKFLOW_NEXT[column.id] ? (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 px-2 text-xs"
                                onClick={(event) => {
                                  event.stopPropagation()
                                  transitionMutation.mutate({
                                    caseId: item.id,
                                    status: WORKFLOW_NEXT[column.id]!,
                                  })
                                }}
                              >
                                Advance
                              </Button>
                            ) : null}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </EnterprisePanel>

          <EnterprisePanel
            title="Knowledge Graph Explorer"
            description={`Model-aligned graph preview with ${kgModelQuery.data?.entity_types?.length ?? '...'} entity types available.`}
          >
            <div className="mb-4 flex flex-wrap gap-2">
              <Input
                value={kgEntityId}
                onChange={(e) => setKgEntityId(e.target.value)}
                placeholder="Lookup entity UUID"
                className="max-w-sm"
              />
              <Button
                size="sm"
                variant="outline"
                className="rounded-sm border-[var(--fs-border)]"
                onClick={() => {
                  kgEntityQuery.refetch()
                  kgNeighborsQuery.refetch()
                }}
                disabled={kgEntityId.trim().length < 8}
              >
                Search graph
              </Button>
            </div>
            {kgEntityQuery.data?.entity ? (
              <div className="mb-4 rounded-md border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className="rounded-sm border border-[var(--fs-border)] bg-transparent text-[var(--fs-text-secondary)]">
                    {String(kgEntityQuery.data.entity.entity_type)}
                  </Badge>
                  <p className="font-mono text-xs text-[var(--fs-accent)]">
                    {String(kgEntityQuery.data.entity.canonical_key)}
                  </p>
                </div>
                <p className="mt-2 text-sm text-[var(--fs-text-primary)]">
                  {String(kgEntityQuery.data.entity.display_name)}
                </p>
              </div>
            ) : null}
            <div className="grid gap-4 lg:grid-cols-3">
              {demoEntities.map((entity) => (
                <EntityCard key={entity.title} entity={entity} compact />
              ))}
            </div>
            {kgNeighborsQuery.data?.neighbors?.length ? (
              <div className="mt-4 space-y-2">
                {kgNeighborsQuery.data.neighbors.slice(0, 4).map((neighbor, index) => (
                  <div
                    key={`${neighbor.relation_type}-${index}`}
                    className="rounded-sm border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] px-3 py-2 text-sm text-[var(--fs-text-secondary)]"
                  >
                    {neighbor.direction === 'out' ? '→' : '←'} {neighbor.relation_type}{' '}
                    {neighbor.entity ? String(neighbor.entity.display_name || neighbor.entity.canonical_key) : ''}
                  </div>
                ))}
              </div>
            ) : null}
          </EnterprisePanel>
        </div>

        <div className="space-y-6">
          <EnterprisePanel
            title="Explainable Risk"
            description="Risk scores never appear without a path back to rules, evidence, and analyst review."
          >
            <div className="space-y-4">
              <div className="rounded-md border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] p-4">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--fs-text-tertiary)]">
                      Current blended score
                    </p>
                    <p className="mt-2 font-mono text-3xl font-semibold text-[var(--fs-text-primary)]">
                      {riskMeta?.xgboost?.blended_score ?? '64'}
                    </p>
                  </div>
                  <RiskBadge level={activeRisk} onClick={() => setDrawerOpen(true)} />
                </div>
                <p className="mt-3 text-xs text-[var(--fs-text-secondary)]">
                  Heuristic {riskMeta?.heuristic_score ?? '59'} · Model {riskMeta?.xgboost?.model_score ?? '68'} · {riskMeta?.xgboost?.model_version ?? 'sovereign-xgb-v1'}
                </p>
              </div>
              <div className="space-y-2">
                {demoEvidence.map((item) => (
                  <EvidenceRow key={item.id} item={item} />
                ))}
              </div>
            </div>
          </EnterprisePanel>

          <EnterprisePanel
            title="API Integration Status"
            description="Secure gateway, sovereign connectors, and workspace module readiness."
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-sm border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] px-3 py-2 text-sm">
                <span className="text-[var(--fs-text-primary)]">Secure gateway</span>
                <Badge className="rounded-sm border border-[var(--fs-border)] bg-transparent text-[var(--fs-accent)]">
                  Online
                </Badge>
              </div>
              <div className="flex items-center justify-between rounded-sm border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] px-3 py-2 text-sm">
                <span className="text-[var(--fs-text-primary)]">Connector catalog</span>
                <span className="text-[var(--fs-text-secondary)]">
                  {connectorsManifestQuery.data?.total ?? '...'} connectors
                </span>
              </div>
              <div className="flex items-center justify-between rounded-sm border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] px-3 py-2 text-sm">
                <span className="text-[var(--fs-text-primary)]">Intelligence engines</span>
                <span className="text-[var(--fs-text-secondary)]">
                  {intelligenceManifestQuery.data?.engines?.length ?? '...'} active
                </span>
              </div>
              <div className="flex items-center justify-between rounded-sm border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] px-3 py-2 text-sm">
                <span className="text-[var(--fs-text-primary)]">Design system modules</span>
                <span className="text-[var(--fs-text-secondary)]">
                  {designSystemManifestQuery.data?.themes?.length ?? '...'} themes
                </span>
              </div>
            </div>
          </EnterprisePanel>

          <EnterprisePanel
            title="Evidence Graph Preview"
            description="Knowledge graph explorer shell for case-linked entities and evidence."
          >
            <div className="h-[420px] overflow-hidden rounded-md border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)]">
              {graphQuery.isLoading || fuseMutation.isPending ? (
                <div className="space-y-3 p-4">
                  <Skeleton className="h-8 w-2/3" />
                  <Skeleton className="h-80 w-full rounded-md" />
                </div>
              ) : flow.nodes.length ? (
                <ReactFlow nodes={flow.nodes} edges={flow.edges} fitView>
                  <Background />
                  <MiniMap />
                  <Controls />
                </ReactFlow>
              ) : (
                <div className="flex h-full items-center justify-center p-6 text-sm text-[var(--fs-text-secondary)]">
                  Create a case and run fusion to populate the graph explorer.
                </div>
              )}
            </div>
          </EnterprisePanel>
        </div>
      </div>

      <ExplainabilityDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        title={activeCase?.case_ref ?? 'Compliance risk explanation'}
        risk={activeRisk}
      />
    </PageLayout>
  )
}

export function CompliancePage() {
  return (
    <ReactFlowProvider>
      <CompliancePageInner />
    </ReactFlowProvider>
  )
}
