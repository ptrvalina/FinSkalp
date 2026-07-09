import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { complianceService, type ComplianceCase, type ComplianceCaseListItem, type EvidenceGraph } from '@/api/compliance-service'
import { PageLayout } from '@/components/layout/page-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { Skeleton } from '@/components/ui/skeleton'

const WORKFLOW_COLUMNS = [
  { id: 'new', label: 'Новое' },
  { id: 'triage', label: 'Триаж' },
  { id: 'investigating', label: 'Расследование' },
  { id: 'pending_filing', label: 'К подаче' },
  { id: 'filed', label: 'Подано' },
  { id: 'archived', label: 'Архив' }
] as const

const WORKFLOW_NEXT: Record<string, string | undefined> = {
  new: 'triage',
  triage: 'investigating',
  investigating: 'pending_filing',
  pending_filing: 'filed',
  filed: 'archived'
}

function graphToFlow(graph?: EvidenceGraph | null): { nodes: Node[]; edges: Edge[] } {
  if (!graph?.nodes?.length) {
    return { nodes: [], edges: [] }
  }
  const nodes: Node[] = graph.nodes.map((node, index) => ({
    id: node.id,
    position: { x: (index % 4) * 220, y: Math.floor(index / 4) * 120 },
    data: {
      label: `${node.label}\n${node.kind}`
    },
    style: {
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 8,
      background: node.kind.includes('wallet') ? '#1f2937' : '#111827',
      color: '#f9fafb',
      fontSize: 12,
      width: 180
    }
  }))
  const edges: Edge[] = graph.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.rel_type,
    animated: (edge.strength ?? 0) >= 0.7
  }))
  return { nodes, edges }
}

function CompliancePageInner() {
  const [caseRef, setCaseRef] = useState(`CASE-${Date.now()}`)
  const [wallet, setWallet] = useState('TRU_HUB_MSK')
  const [scenarioId, setScenarioId] = useState('p2p_rub_offshore')
  const [activeCase, setActiveCase] = useState<ComplianceCase | null>(null)
  const [kgEntityId, setKgEntityId] = useState('')
  const [kgVersionA, setKgVersionA] = useState('1')
  const [kgVersionB, setKgVersionB] = useState('2')

  const graphQuery = useQuery({
    queryKey: ['compliance', 'graph', activeCase?.id],
    queryFn: () => complianceService.getGraph(activeCase!.id),
    enabled: Boolean(activeCase?.id && activeCase.status !== 'draft')
  })

  const casesQuery = useQuery({
    queryKey: ['compliance', 'cases'],
    queryFn: () => complianceService.listCases(),
    refetchInterval: 30_000
  })

  const workflowStatsQuery = useQuery({
    queryKey: ['compliance', 'workflow-stats'],
    queryFn: () => complianceService.getWorkflowStats()
  })

  const kgModelQuery = useQuery({
    queryKey: ['compliance', 'kg-model'],
    queryFn: () => complianceService.getKnowledgeModel()
  })

  const kgEntityQuery = useQuery({
    queryKey: ['compliance', 'kg-entity', kgEntityId],
    queryFn: () => complianceService.getKgEntity(kgEntityId.trim()),
    enabled: kgEntityId.trim().length >= 8
  })

  const kgNeighborsQuery = useQuery({
    queryKey: ['compliance', 'kg-neighbors', kgEntityId],
    queryFn: () => complianceService.getKgEntityNeighbors(kgEntityId.trim()),
    enabled: Boolean(kgEntityQuery.data?.entity)
  })

  const pipelineChainQuery = useQuery({
    queryKey: ['compliance', 'pipeline-chain'],
    queryFn: () => complianceService.getPipelineChain()
  })

  const intelligenceManifestQuery = useQuery({
    queryKey: ['compliance', 'intelligence-manifest'],
    queryFn: () => complianceService.getIntelligenceManifest()
  })

  const investigationManifestQuery = useQuery({
    queryKey: ['compliance', 'investigation-manifest'],
    queryFn: () => complianceService.getInvestigationManifest()
  })

  const intelligenceEngineManifestQuery = useQuery({
    queryKey: ['compliance', 'intelligence-engine-manifest'],
    queryFn: () => complianceService.getIntelligenceEngineManifest()
  })

  const connectorsManifestQuery = useQuery({
    queryKey: ['compliance', 'connectors-manifest'],
    queryFn: () => complianceService.getConnectorsManifest()
  })

  const designSystemManifestQuery = useQuery({
    queryKey: ['compliance', 'design-system-manifest'],
    queryFn: () => complianceService.getDesignSystemManifest()
  })

  const rbacManifestQuery = useQuery({
    queryKey: ['compliance', 'rbac-manifest'],
    queryFn: () => complianceService.getRbacManifest()
  })

  const workflowManifestQuery = useQuery({
    queryKey: ['compliance', 'workflow-manifest'],
    queryFn: () => complianceService.getWorkflowManifest()
  })

  const blockchainManifestQuery = useQuery({
    queryKey: ['compliance', 'blockchain-intelligence-manifest'],
    queryFn: () => complianceService.getBlockchainIntelligenceManifest()
  })

  const icfManifestQuery = useQuery({
    queryKey: ['compliance', 'icf-manifest'],
    queryFn: () => complianceService.getIcfManifest()
  })

  const crifManifestQuery = useQuery({
    queryKey: ['compliance', 'crif-manifest'],
    queryFn: () => complianceService.getCrifManifest()
  })

  const rdeManifestQuery = useQuery({
    queryKey: ['compliance', 'rde-manifest'],
    queryFn: () => complianceService.getRdeManifest()
  })

  const eccfManifestQuery = useQuery({
    queryKey: ['compliance', 'eccf-manifest'],
    queryFn: () => complianceService.getEccfManifest()
  })

  const analystWorkspaceManifestQuery = useQuery({
    queryKey: ['compliance', 'analyst-workspace-manifest'],
    queryFn: () => complianceService.getAnalystWorkspaceManifest()
  })

  const workspaceQuery = useQuery({
    queryKey: ['compliance', 'investigation-workspace', activeCase?.case_ref],
    queryFn: () => complianceService.getInvestigationWorkspace(activeCase!.case_ref),
    enabled: Boolean(activeCase?.case_ref)
  })

  const kgCompareQuery = useQuery({
    queryKey: ['compliance', 'kg-compare', kgEntityId, kgVersionA, kgVersionB],
    queryFn: () =>
      complianceService.compareKgEntityVersions(
        kgEntityId.trim(),
        Number(kgVersionA),
        Number(kgVersionB)
      ),
    enabled: kgEntityId.trim().length >= 8 && Number(kgVersionA) > 0 && Number(kgVersionB) > 0
  })

  const transitionMutation = useMutation({
    mutationFn: ({ caseId, status }: { caseId: string; status: string }) =>
      complianceService.transitionCase(caseId, status),
    onSuccess: () => {
      casesQuery.refetch()
      workflowStatsQuery.refetch()
      toast.success('Статус дела обновлён')
    },
    onError: (error: Error) => toast.error(error.message)
  })

  /** Viewer role: read-only kanban (no transitions). Set VITE_COMPLIANCE_VIEWER=1 to preview. */
  const readOnlyWorkflow = import.meta.env.VITE_COMPLIANCE_VIEWER === '1'

  const createMutation = useMutation({
    mutationFn: () => complianceService.createCase(caseRef),
    onSuccess: (created) => {
      setActiveCase(created)
      toast.success(`Кейс ${created.case_ref} создан`)
    },
    onError: (error: Error) => toast.error(error.message)
  })

  const fuseMutation = useMutation({
    mutationFn: () => complianceService.fuseCase(activeCase!.id, scenarioId),
    onSuccess: async () => {
      const refreshed = await complianceService.getCase(activeCase!.id)
      setActiveCase(refreshed)
      graphQuery.refetch()
      toast.success('OSINT Fusion завершён')
    },
    onError: (error: Error) => toast.error(error.message)
  })

  const demoMutation = useMutation({
    mutationFn: () => complianceService.seedDemo(scenarioId),
    onSuccess: (report: Record<string, unknown>) => {
      toast.success(`Демо: risk ${report.illegal_flow_score}/100`)
      if (report.case_ref) {
        setCaseRef(String(report.case_ref))
      }
    },
    onError: (error: Error) => toast.error(error.message)
  })

  const screenMutation = useMutation({
    mutationFn: () => complianceService.screenWallet(wallet),
    onSuccess: (result: Record<string, unknown>) => {
      toast.success(`Скрининг: ${result.risk_score}/100 (${result.risk_level})`)
    },
    onError: (error: Error) => toast.error(error.message)
  })

  const intelligenceMutation = useMutation({
    mutationFn: () =>
      complianceService.runIntelligenceAnalysis({
        address: wallet,
        chain: 'tron',
        case_ref: activeCase?.case_ref,
        publish: true
      }),
    onSuccess: (result) => {
      toast.success(
        `Анализ RFC-0004: риск ${result.aggregate_risk_score.toFixed(1)}/100 (${result.risk_level}), движков: ${result.engines_run.length}`
      )
    },
    onError: (error: Error) => toast.error(error.message)
  })

  const intelligenceEngineMutation = useMutation({
    mutationFn: () =>
      complianceService.runIntelligenceEngine({
        address: wallet,
        chain: 'tron',
        case_ref: activeCase?.case_ref,
        publish: true
      }),
    onSuccess: (result) => {
      const w = result.weakest_score
      toast.success(
        `RFC-0006: гипотез ${result.hypotheses.length}, слабый показатель ${w.metric} (${w.value})`
      )
    },
    onError: (error: Error) => toast.error(error.message)
  })

  const flow = useMemo(() => graphToFlow(graphQuery.data), [graphQuery.data])
  const riskMeta = (activeCase?.fusion_result as Record<string, any> | undefined)?.metrics
    ?.risk_scoring as Record<string, any> | undefined

  const casesByWorkflow = useMemo(() => {
    const map: Record<string, ComplianceCaseListItem[]> = Object.fromEntries(
      WORKFLOW_COLUMNS.map((c) => [c.id, []])
    )
    for (const c of casesQuery.data ?? []) {
      const ws = c.workflow_status || 'new'
      ;(map[ws] ?? map.new).push(c)
    }
    return map
  }, [casesQuery.data])

  return (
    <PageLayout title="Compliance 115-ФЗ" description="OSINT Fusion · суверенный реестр · XGBoost risk">
      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Кейс</CardTitle>
            <CardDescription>Создание и fusion на суверенных источниках РФ/СНГ</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input value={caseRef} onChange={(e) => setCaseRef(e.target.value)} placeholder="CASE-2026-001" />
            <Input
              value={scenarioId}
              onChange={(e) => setScenarioId(e.target.value)}
              placeholder="p2p_rub_offshore"
            />
            <Button className="w-full" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              Создать кейс
            </Button>
            <Button
              className="w-full"
              variant="secondary"
              disabled={!activeCase || fuseMutation.isPending}
              onClick={() => fuseMutation.mutate()}
            >
              Запустить Fusion
            </Button>
            <Button className="w-full" variant="outline" onClick={() => demoMutation.mutate()} disabled={demoMutation.isPending}>
              Демо-сценарий
            </Button>
            {activeCase?.fusion_result && (
              <div className="flex gap-2">
                <Button variant="outline" size="sm" asChild>
                  <a href={complianceService.reportPdfUrl(activeCase.id)} target="_blank" rel="noreferrer">
                    PDF
                  </a>
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <a href={complianceService.reportXlsxUrl(activeCase.id)} target="_blank" rel="noreferrer">
                    Excel
                  </a>
                </Button>
              </div>
            )}
            {activeCase && (
              <div className="text-sm space-y-1">
                <div>ID: <code>{activeCase.id}</code></div>
                <div>Статус: <Badge>{activeCase.status}</Badge></div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Скрининг кошелька</CardTitle>
            <CardDescription>On-chain + реестр 115-ФЗ + XGBoost</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input value={wallet} onChange={(e) => setWallet(e.target.value)} placeholder="TRON / ETH / BTC адрес" />
            <Button className="w-full" disabled={!wallet || screenMutation.isPending} onClick={() => screenMutation.mutate()}>
              Проверить кошелёк
            </Button>
            <Button
              className="w-full"
              variant="secondary"
              disabled={!wallet || intelligenceMutation.isPending}
              onClick={() => intelligenceMutation.mutate()}
            >
              Запустить анализ
            </Button>
            <Button
              className="w-full"
              variant="outline"
              disabled={!wallet || intelligenceEngineMutation.isPending}
              onClick={() => intelligenceEngineMutation.mutate()}
            >
              Intelligence Engine (RFC-0006)
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>XGBoost risk</CardTitle>
            <CardDescription>Модель типологий 115-ФЗ (sovereign-xgb-v1)</CardDescription>
          </CardHeader>
          <CardContent className="text-sm space-y-2">
            {riskMeta?.xgboost ? (
              <>
                <div>Blended: <strong>{riskMeta.xgboost.blended_score}</strong></div>
                <div>Heuristic: {riskMeta.heuristic_score}</div>
                <div>Model: {riskMeta.xgboost.model_score}</div>
                <div className="text-muted-foreground">{riskMeta.xgboost.model_version}</div>
              </>
            ) : (
              <p className="text-muted-foreground">Запустите fusion или демо-сценарий для расчёта модели.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Конвейер дел · Kanban</CardTitle>
          <CardDescription>
            {readOnlyWorkflow
              ? 'Режим просмотра (viewer) — переходы статусов отключены'
              : 'Workflow API · RBAC на backend (viewer = только чтение)'}
            {workflowStatsQuery.data ? (
              <span className="ml-2 text-muted-foreground">
                · SLA breach: {workflowStatsQuery.data.sla_breached}
              </span>
            ) : null}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {casesQuery.isLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : (
            <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-6 overflow-x-auto">
              {WORKFLOW_COLUMNS.map((col) => (
                <div key={col.id} className="rounded-lg border bg-muted/30 p-2 min-w-[140px]">
                  <div className="flex justify-between text-xs font-medium mb-2 text-muted-foreground">
                    <span>{col.label}</span>
                    <Badge variant="outline">{casesByWorkflow[col.id]?.length ?? 0}</Badge>
                  </div>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {(casesByWorkflow[col.id] ?? []).map((c) => (
                      <div
                        key={c.id}
                        className={`rounded border bg-background p-2 text-xs ${c.sla_breached ? 'border-destructive' : ''}`}
                      >
                        <div className="font-mono font-medium">{c.case_ref}</div>
                        <div className="text-muted-foreground mt-1">{c.priority ?? 'normal'}</div>
                        {!readOnlyWorkflow && WORKFLOW_NEXT[col.id] ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="mt-1 h-6 px-2 text-xs"
                            disabled={transitionMutation.isPending}
                            onClick={() =>
                              transitionMutation.mutate({
                                caseId: c.id,
                                status: WORKFLOW_NEXT[col.id]!
                              })
                            }
                          >
                            → далее
                          </Button>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Граф знаний</CardTitle>
          <CardDescription>
            RFC-0003 · единая модель данных · {kgModelQuery.data?.entity_types?.length ?? '…'} типов сущностей
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              value={kgEntityId}
              onChange={(e) => setKgEntityId(e.target.value)}
              placeholder="UUID сущности (entity_id)"
            />
            <Button
              variant="secondary"
              disabled={kgEntityId.trim().length < 8}
              onClick={() => {
                kgEntityQuery.refetch()
                kgNeighborsQuery.refetch()
              }}
            >
              Найти
            </Button>
          </div>
          {kgModelQuery.isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : kgModelQuery.data ? (
            <div className="flex flex-wrap gap-1">
              {kgModelQuery.data.entity_types.slice(0, 12).map((t) => (
                <Badge key={t.value} variant="outline">
                  {t.label_ru}
                </Badge>
              ))}
            </div>
          ) : null}
          {kgEntityQuery.isFetching ? (
            <Skeleton className="h-20 w-full" />
          ) : kgEntityQuery.data?.entity ? (
            <div className="rounded-lg border p-3 text-sm space-y-2">
              <div>
                <span className="text-muted-foreground">Тип: </span>
                <Badge>{String(kgEntityQuery.data.entity.entity_type)}</Badge>
              </div>
              <div>
                <span className="text-muted-foreground">Ключ: </span>
                <code>{String(kgEntityQuery.data.entity.canonical_key)}</code>
              </div>
              <div>
                <span className="text-muted-foreground">Имя: </span>
                {String(kgEntityQuery.data.entity.display_name)}
              </div>
            </div>
          ) : kgEntityId.trim().length >= 8 && kgEntityQuery.isError ? (
            <p className="text-sm text-muted-foreground">Сущность не найдена</p>
          ) : null}
          {kgNeighborsQuery.data?.neighbors?.length ? (
            <div className="space-y-2">
              <div className="text-sm font-medium">Соседи ({kgNeighborsQuery.data.count})</div>
              <ul className="text-sm space-y-1 max-h-48 overflow-y-auto">
                {kgNeighborsQuery.data.neighbors.map((n, i) => (
                  <li key={`${n.relation_type}-${i}`} className="rounded border px-2 py-1">
                    <span className="text-muted-foreground">{n.direction === 'out' ? '→' : '←'} </span>
                    {n.relation_type}
                    {n.entity ? (
                      <span className="ml-2 text-muted-foreground">
                        {String(n.entity.display_name || n.entity.canonical_key)}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <div className="flex flex-wrap gap-2 items-end">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Сравнение версий</div>
              <div className="flex gap-2">
                <Input
                  className="w-16"
                  value={kgVersionA}
                  onChange={(e) => setKgVersionA(e.target.value)}
                  placeholder="v1"
                />
                <Input
                  className="w-16"
                  value={kgVersionB}
                  onChange={(e) => setKgVersionB(e.target.value)}
                  placeholder="v2"
                />
                <Button
                  variant="outline"
                  size="sm"
                  disabled={kgEntityId.trim().length < 8}
                  onClick={() => kgCompareQuery.refetch()}
                >
                  Сравнить
                </Button>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                try {
                  const data = await complianceService.exportKgEvidence(activeCase?.case_ref)
                  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `evidence-export-${activeCase?.case_ref || 'all'}.json`
                  a.click()
                  URL.revokeObjectURL(url)
                  toast.success(`Экспорт: ${data.evidence_count} доказательств`)
                } catch (e) {
                  toast.error(e instanceof Error ? e.message : 'Ошибка экспорта')
                }
              }}
            >
              Экспорт доказательств
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                try {
                  await complianceService.createGraphSnapshot()
                  toast.success('Снимок графа создан')
                } catch (e) {
                  toast.error(e instanceof Error ? e.message : 'Ошибка снимка')
                }
              }}
            >
              Снимок графа
            </Button>
          </div>
          {kgCompareQuery.data && !('error' in kgCompareQuery.data) ? (
            <div className="rounded-lg border p-3 text-xs space-y-1">
              <div className="font-medium">Изменения v{kgVersionA} → v{kgVersionB}</div>
              {Boolean((kgCompareQuery.data as { display_name_changed?: boolean }).display_name_changed) && (
                <div>Имя изменено</div>
              )}
              <pre className="overflow-auto max-h-32">
                {JSON.stringify(
                  (kgCompareQuery.data as { changed_attributes?: unknown }).changed_attributes || {},
                  null,
                  2
                )}
              </pre>
            </div>
          ) : null}
          {pipelineChainQuery.data ? (
            <div className="text-xs text-muted-foreground">
              Цепочка RFC-0003:{' '}
              {pipelineChainQuery.data.stages.map((s) => s.label_ru).join(' → ')}
            </div>
          ) : null}
          {intelligenceManifestQuery.data ? (
            <div className="space-y-2">
              <div className="text-sm font-medium">RFC-0004 · {intelligenceManifestQuery.data.engines.length} движков</div>
              <div className="flex flex-wrap gap-1">
                {intelligenceManifestQuery.data.engines.map((e) => (
                  <Badge key={e.engine} variant="secondary">
                    {e.title_ru}
                  </Badge>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">{intelligenceManifestQuery.data.rule_ru}</p>
            </div>
          ) : null}
          {investigationManifestQuery.data ? (
            <div className="space-y-2">
              <div className="text-sm font-medium">
                RFC-0005 · {investigationManifestQuery.data.workspace_panels.length} панелей workspace
              </div>
              {workspaceQuery.data ? (
                <p className="text-xs text-muted-foreground">
                  Доказательств: {workspaceQuery.data.evidence_count} · Событий: {workspaceQuery.data.timeline_count}
                </p>
              ) : null}
              <p className="text-xs text-muted-foreground">{investigationManifestQuery.data.principle_ru}</p>
            </div>
          ) : null}
          {intelligenceEngineManifestQuery.data ? (
            <div className="space-y-1">
              <div className="text-sm font-medium">RFC-0006 · {intelligenceEngineManifestQuery.data.score_metrics.length} метрик</div>
              <p className="text-xs text-muted-foreground">{intelligenceEngineManifestQuery.data.philosophy_ru}</p>
            </div>
          ) : null}
          {connectorsManifestQuery.data ? (
            <div className="space-y-1">
              <div className="text-sm font-medium">
                RFC-0007 · {connectorsManifestQuery.data.total} коннекторов
              </div>
              <p className="text-xs text-muted-foreground">
                Категории: {connectorsManifestQuery.data.categories.join(', ')}
              </p>
            </div>
          ) : null}
          {designSystemManifestQuery.data ? (
            <div className="space-y-1">
              <div className="text-sm font-medium">
                RFC-0008 · {designSystemManifestQuery.data.themes.length} темы ·{' '}
                {designSystemManifestQuery.data.entity_icons.length} иконок сущностей
              </div>
              <p className="text-xs text-muted-foreground">{designSystemManifestQuery.data.philosophy_ru}</p>
            </div>
          ) : null}
          {rbacManifestQuery.data ? (
            <div className="space-y-1">
              <div className="text-sm font-medium">
                RFC-0009 · {rbacManifestQuery.data.planes.compliance.length} compliance ·{' '}
                {rbacManifestQuery.data.planes.investigation.length} investigation ролей
              </div>
              <p className="text-xs text-muted-foreground">{rbacManifestQuery.data.rule_ru}</p>
            </div>
          ) : null}
          {workflowManifestQuery.data ? (
            <div className="space-y-1">
              <div className="text-sm font-medium">
                RFC-0011 · {workflowManifestQuery.data.investigation_lifecycle.length} этапов · OICD
              </div>
              <p className="text-xs text-muted-foreground">{workflowManifestQuery.data.principle_ru}</p>
            </div>
          ) : null}
          {blockchainManifestQuery.data ? (
            <div className="space-y-1">
              <div className="text-sm font-medium">
                RFC-0012 · {blockchainManifestQuery.data.supported_networks.length} сетей ·{' '}
                {blockchainManifestQuery.data.canonical_entities.length} сущностей модели
              </div>
              <p className="text-xs text-muted-foreground">{blockchainManifestQuery.data.principle_ru}</p>
            </div>
          ) : null}
          {icfManifestQuery.data ? (
            <div className="space-y-1">
              <div className="text-sm font-medium">
                RFC-0014 · {icfManifestQuery.data.pipeline.length} стадий ·{' '}
                {icfManifestQuery.data.collector_count} коллекторов
              </div>
              <p className="text-xs text-muted-foreground">{icfManifestQuery.data.principle_ru}</p>
            </div>
          ) : null}
          {crifManifestQuery.data ? (
            <div className="space-y-1">
              <div className="text-sm font-medium">
                RFC-0015 · {crifManifestQuery.data.pipeline.length} стадий ·{' '}
                {crifManifestQuery.data.connector_count} реестровых коннекторов ·{' '}
                {crifManifestQuery.data.canonical_entity_types.length} типов сущностей
              </div>
              <p className="text-xs text-muted-foreground">{crifManifestQuery.data.principle_ru}</p>
            </div>
          ) : null}
          {rdeManifestQuery.data ? (
            <div className="space-y-1">
              <div className="text-sm font-medium">
                RFC-0016 · {rdeManifestQuery.data.pipeline.length} стадий ·{' '}
                {rdeManifestQuery.data.factor_groups.length} факторных групп ·{' '}
                {rdeManifestQuery.data.risk_levels.length} уровней риска
              </div>
              <p className="text-xs text-muted-foreground">{rdeManifestQuery.data.principle_ru}</p>
            </div>
          ) : null}
          {eccfManifestQuery.data ? (
            <div className="space-y-1">
              <div className="text-sm font-medium">
                RFC-0017 · {eccfManifestQuery.data.pipeline.length} стадий ·{' '}
                {eccfManifestQuery.data.evidence_categories.length} категорий доказательств ·{' '}
                {eccfManifestQuery.data.audit_actions.length} типов аудита
              </div>
              <p className="text-xs text-muted-foreground">{eccfManifestQuery.data.principle_ru}</p>
            </div>
          ) : null}
          {analystWorkspaceManifestQuery.data ? (
            <div className="space-y-1">
              <div className="text-sm font-medium">
                RFC-0010 · {analystWorkspaceManifestQuery.data.workspace_tabs.length} вкладок ·{' '}
                {analystWorkspaceManifestQuery.data.command_palette.length} команд
              </div>
              <p className="text-xs text-muted-foreground">
                {analystWorkspaceManifestQuery.data.principle_ru}
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Граф доказательств</CardTitle>
          <CardDescription>Evidence graph (PostgreSQL + Neo4j export)</CardDescription>
        </CardHeader>
        <CardContent className="h-[520px]">
          {graphQuery.isLoading || fuseMutation.isPending ? (
            <div className="space-y-3 h-full">
              <Skeleton className="h-8 w-2/3" />
              <Skeleton className="h-[420px] w-full rounded-lg" />
            </div>
          ) : flow.nodes.length ? (
            <ReactFlow nodes={flow.nodes} edges={flow.edges} fitView>
              <Background />
              <MiniMap />
              <Controls />
            </ReactFlow>
          ) : (
            <div className="text-muted-foreground text-sm">Нет данных графа — создайте кейс и выполните fusion.</div>
          )}
        </CardContent>
      </Card>
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
