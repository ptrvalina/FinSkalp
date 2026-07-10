import { useCallback, useEffect, useMemo, useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { Link } from '@tanstack/react-router'

import {

  Bell,

  ExternalLink,

  LayoutDashboard,

  Send,

} from 'lucide-react'

import { complianceService } from '@/api/compliance-service'

import {

  apiPayloadToPersonalization,

  loadWorkspacePersonalization,

  personalizationToApiPayload,

  saveWorkspacePersonalization,

  useInvestigationUiContext,

  useWorkspaceSync,

} from '@/design-system'

import { ActivityTimeline } from '@/components/dashboard/investigation/activity-timeline'

import { Badge } from '@/components/ui/badge'

import { Button } from '@/components/ui/button'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import { Input } from '@/components/ui/input'

import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

import { Skeleton } from '@/components/ui/skeleton'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { useTheme } from '@/components/theme-provider'

import { WorkspaceCommandPalette } from './workspace-command-palette'
import { CaseDashboardPanel } from './case-dashboard-panel'
import { RiskDrawerPanel } from './risk-drawer-panel'
import { WorkspaceEvidenceSection } from './workspace-evidence-section'
import { GraphInsightsPanel } from './graph-insights-panel'
import { AiContextPanel } from './ai-context-panel'
import { TaskBoardPanel } from './task-board-panel'
import { BookmarksPanel } from './bookmarks-panel'
import { ActivityFeedPanel } from './activity-feed-panel'
import { QuickActionsBar } from './quick-actions-bar'
import { ReportsPanel } from './reports-panel'
import { WalletsPanel } from './wallets-panel'
import { AlertCenterPanel } from './alert-center-panel'
import {
  EnterpriseContextBar,
  EnterprisePanel,
  EntityCard,
} from '@/components/enterprise/enterprise-ui'



const TAB_LABELS: Record<string, string> = {

  summary: 'Сводка',

  entities: 'Сущности',

  wallets: 'Кошельки',

  timeline: 'Хронология',

  evidence: 'Доказательства',

  graph: 'Граф',

  reports: 'Отчёты',

  activity: 'Активность',

  tasks: 'Задачи',

  bookmarks: 'Закладки',

  ai: 'AI Context',

}



type Props = {

  investigationId: string

  investigationName: string

  caseRef: string | null

  linkedCaseLoading?: boolean

}



function formatNotifTime(iso?: string) {

  if (!iso) return ''

  try {

    return new Date(iso).toLocaleString('ru-RU')

  } catch {

    return iso

  }

}



export function AnalystWorkspaceShell({

  investigationId,

  investigationName,

  caseRef,

  linkedCaseLoading,

}: Props) {

  const queryClient = useQueryClient()

  const { theme, setTheme } = useTheme()

  const { context, setInvestigationId, setCaseRef, setSelectedEntityId, setFilters } =

    useInvestigationUiContext()

  const [activeTab, setActiveTab] = useState(() => loadWorkspacePersonalization(caseRef).activeTab)

  const [paletteOpen, setPaletteOpen] = useState(false)

  const [commentText, setCommentText] = useState('')

  const [notificationsOpen, setNotificationsOpen] = useState(false)

  const [readNotificationIds, setReadNotificationIds] = useState<Set<string>>(new Set())

  const [drawerOpen, setDrawerOpen] = useState(false)



  useEffect(() => {

    setInvestigationId(investigationId)

  }, [investigationId, setInvestigationId])



  useEffect(() => {

    setCaseRef(caseRef)

  }, [caseRef, setCaseRef])



  useEffect(() => {

    if (!caseRef) return

    const local = loadWorkspacePersonalization(caseRef)

    setActiveTab(local.activeTab)

    complianceService

      .getAnalystWorkspacePersonalization()

      .then((res) => {

        if (res.ok && res.preferences) {

          const merged = apiPayloadToPersonalization(res.preferences)

          saveWorkspacePersonalization(merged, caseRef)

          setActiveTab(merged.activeTab)

        }

      })

      .catch(() => {

        /* local prefs only */

      })

  }, [caseRef])



  const manifestQuery = useQuery({

    queryKey: ['compliance', 'analyst-workspace-manifest'],

    queryFn: () => complianceService.getAnalystWorkspaceManifest(),

  })



  const stateQuery = useQuery({
    queryKey: ['compliance', 'analyst-workspace-state', caseRef, investigationId],
    queryFn: () =>
      complianceService.getAnalystWorkspaceState({
        caseRef: caseRef!,
        investigationId,
      }),
    enabled: Boolean(caseRef),
    refetchInterval: 30_000,
  })

  const workflowRecsQuery = useQuery({
    queryKey: ['compliance', 'workflow-recommendations', caseRef],
    queryFn: () => complianceService.getWorkflowRecommendations(caseRef!),
    enabled: Boolean(caseRef),
  })



  const handleTabChange = useCallback(

    (tab: string) => {

      setActiveTab(tab)

      if (caseRef) {

        const prefs = saveWorkspacePersonalization({ activeTab: tab }, caseRef)

        complianceService

          .saveAnalystWorkspacePersonalization(personalizationToApiPayload(prefs))

          .catch(() => undefined)

      }

    },

    [caseRef]

  )



  useWorkspaceSync({

    selectedEntityId: context.selectedEntityId,

    caseRef,

    activeTab,

    filters: context.filters,

    onRemoteUpdate: (payload) => {

      if (payload.caseRef && payload.caseRef !== caseRef) return

      if (payload.activeTab) setActiveTab(payload.activeTab)

      if (payload.selectedEntityId !== undefined) setSelectedEntityId(payload.selectedEntityId)

      if (payload.filters) setFilters(payload.filters)

    },

  })



  const commentMutation = useMutation({

    mutationFn: (text: string) =>

      complianceService.postAnalystWorkspaceComment({ caseRef: caseRef!, text }),

    onSuccess: () => {

      setCommentText('')

      queryClient.invalidateQueries({

        queryKey: ['compliance', 'analyst-workspace-state', caseRef, investigationId],

      })

    },

  })



  const handlePaletteCommand = useCallback((commandId: string) => {

    const tabMap: Record<string, string> = {

      open_summary: 'summary',

      open_entities: 'entities',

      open_wallets: 'wallets',

      open_timeline: 'timeline',

      open_evidence: 'evidence',

      open_graph: 'graph',

      open_reports: 'reports',

      open_activity: 'activity',

      open_tasks: 'tasks',

      open_bookmarks: 'bookmarks',

      open_ai: 'ai',

      ask_ai: 'ai',

    }

    if (tabMap[commandId]) {

      handleTabChange(tabMap[commandId])

    }

    if (commandId === 'toggle_theme') {
      setTheme(theme === 'dark' ? 'light' : 'dark')
    }
  }, [handleTabChange, theme, setTheme])



  const handleSearchSelect = useCallback(

    (result: { kind: string; id: string; case_ref?: string }) => {

      if (result.kind === 'entity' || result.kind === 'case') {

        setSelectedEntityId(result.id)

        handleTabChange('entities')

      } else if (result.kind === 'evidence') {

        handleTabChange('evidence')

      }

    },

    [handleTabChange, setSelectedEntityId]

  )



  useEffect(() => {

    const onKeyDown = (e: KeyboardEvent) => {

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {

        e.preventDefault()

        setPaletteOpen(true)

        return

      }

      if (!(e.ctrlKey || e.metaKey) || e.shiftKey) return

      const tabByDigit: Record<string, string> = {

        '1': 'summary',

        '2': 'entities',

        '3': 'wallets',

        '4': 'timeline',

        '5': 'evidence',

        '6': 'graph',

        '7': 'reports',

        '8': 'activity',

        '9': 'tasks',

        '0': 'bookmarks',

      }

      const tab = tabByDigit[e.key]

      if (tab) {

        e.preventDefault()

        handleTabChange(tab)

      }

    }

    window.addEventListener('keydown', onKeyDown)

    return () => window.removeEventListener('keydown', onKeyDown)

  }, [handleTabChange])



  const tabs = useMemo(

    () => manifestQuery.data?.workspace_tabs ?? Object.keys(TAB_LABELS),

    [manifestQuery.data]

  )



  const notifications = stateQuery.data?.notifications ?? []

  const unreadCount = useMemo(

    () => notifications.filter((n) => !readNotificationIds.has(n.id) && !n.read).length,

    [notifications, readNotificationIds]

  )



  const collaborationComments = stateQuery.data?.collaboration?.comments ?? []

  const collaborationActivity = stateQuery.data?.collaboration?.activity ?? []



  if (linkedCaseLoading) {

    return (

      <Card>

        <CardHeader>

          <CardTitle className="text-base">Рабочее пространство аналитика</CardTitle>

          <CardDescription>Загрузка…</CardDescription>

        </CardHeader>

        <CardContent>

          <Skeleton className="h-10 w-full" />

        </CardContent>

      </Card>

    )

  }



  if (!caseRef) {

    return null

  }



  const workflow = stateQuery.data?.workspace?.workflow as Record<string, unknown> | undefined

  const counts = stateQuery.data?.counts



  return (

    <div className="space-y-4">

      <EnterprisePanel
        title="Analyst Workspace Shell"
        description="Investigation-first context bar, explainable risk, and persistent workspace state."
        actions={<div className="flex flex-wrap gap-2 items-center">

              <Popover open={notificationsOpen} onOpenChange={setNotificationsOpen}>

                <PopoverTrigger asChild>

                  <Button size="sm" variant="outline" className="relative">

                    <Bell className="w-4 h-4" />

                    {unreadCount > 0 ? (

                      <span className="absolute -top-1 -right-1 bg-destructive text-destructive-foreground text-[10px] rounded-full min-w-4 h-4 flex items-center justify-center px-1">

                        {unreadCount > 9 ? '9+' : unreadCount}

                      </span>

                    ) : null}

                  </Button>

                </PopoverTrigger>

                <PopoverContent className="w-80 p-0" align="end">

                  <div className="p-3 border-b font-medium text-sm">Уведомления</div>

                  <div className="max-h-64 overflow-y-auto">

                    {notifications.length === 0 ? (

                      <p className="p-3 text-sm text-muted-foreground">Нет уведомлений</p>

                    ) : (

                      notifications.map((n) => (

                        <button

                          key={n.id}

                          type="button"

                          className="w-full text-left p-3 text-sm hover:bg-muted/50 border-b last:border-0"

                          onClick={() => setReadNotificationIds((prev) => new Set(prev).add(n.id))}

                        >

                          <div className="font-medium">{n.label_ru}</div>

                          {n.actor ? (

                            <div className="text-xs text-muted-foreground">{n.actor}</div>

                          ) : null}

                          <div className="text-xs text-muted-foreground/70">

                            {formatNotifTime(n.occurred_at)}

                          </div>

                        </button>

                      ))

                    )}

                  </div>

                </PopoverContent>

              </Popover>

              <Button size="sm" variant="outline" onClick={() => setPaletteOpen(true)}>

                Command Palette (Ctrl+K)

              </Button>

              <Button size="sm" variant="outline" asChild>

                <Link to="/dashboard/compliance">

                  Compliance

                  <ExternalLink className="w-3.5 h-3.5 ml-1.5" />

                </Link>

              </Button>

            </div>}
      >
        <div className="space-y-4">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <LayoutDashboard className="w-4 h-4" />
              Investigation Workspace
            </CardTitle>
            <CardDescription className="font-mono mt-1">{caseRef}</CardDescription>
            <p className="text-xs text-muted-foreground mt-1">{investigationName}</p>
          </div>

          <EnterpriseContextBar
            caseId={caseRef}
            status={String(workflow?.workflow_status ?? 'active')}
            priority="medium"
            owner="Assigned analyst"
            risk="high"
            objectCount={String(counts?.timeline ?? 0)}
            evidenceCount={String(counts?.evidence ?? 0)}
          />

          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">RFC-0010</Badge>

            {workflow?.workflow_status ? (
              <Badge variant="secondary">{String(workflow.workflow_status)}</Badge>
            ) : null}

            {counts ? (
              <>
                <Badge variant="outline">{counts.evidence} evidence</Badge>
                <Badge variant="outline">{counts.timeline} events</Badge>
              </>
            ) : null}

            {stateQuery.data?.intelligence ? (
              <Badge variant="outline">{stateQuery.data.intelligence.engines_count} engines</Badge>
            ) : null}

            {stateQuery.data?.latency_ms != null ? (
              <Badge variant="outline" className="font-mono text-xs">
                {stateQuery.data.latency_ms} ms
              </Badge>
            ) : null}
          </div>
        </div>
      </EnterprisePanel>

      <QuickActionsBar onAction={handlePaletteCommand} />



      <Tabs value={activeTab} onValueChange={handleTabChange}>

        <TabsList className="flex flex-wrap h-auto gap-1 rounded-sm border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] p-1">

          {tabs.map((tab) => (

            <TabsTrigger key={tab} value={tab} className="text-xs sm:text-sm">

              {manifestQuery.data?.workspace_tabs_ru?.[tab] ?? TAB_LABELS[tab] ?? tab}

            </TabsTrigger>

          ))}

        </TabsList>



        <TabsContent value="summary" className="mt-4">

          <CaseDashboardPanel
            caseRef={caseRef}
            investigationName={investigationName}
            workflow={workflow}
            counts={counts}
            intelligence={stateQuery.data?.intelligence}
            recommendations={workflowRecsQuery.data?.recommendations}
            onOpenRisk={() => setDrawerOpen(true)}
          />

        </TabsContent>



        <TabsContent value="entities" className="mt-4">

          <EnterprisePanel title="Entities" description="Compact entity views keep focus on attribution, sources, and risk.">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {[0, 1, 2].map((index) => (
                <EntityCard
                  key={index}
                  compact
                  entity={{
                    title: index === 0 && context.selectedEntityId ? context.selectedEntityId : `Workspace Entity ${index + 1}`,
                    subtitle: index === 1 ? 'Counterparty' : 'Graph entity',
                    attributes: [
                      'Entity-first evidence context',
                      'Selection preserved across route changes',
                      'Ready for graph and reporting pivots',
                    ],
                    sources: ['Evidence', 'Registry', 'OSINT'],
                    confidence: 72 + index * 8,
                    risk: index === 0 ? 'high' : index === 1 ? 'medium' : 'low',
                  }}
                />
              ))}
            </div>
          </EnterprisePanel>

        </TabsContent>



        <TabsContent value="wallets" className="mt-4">
          <WalletsPanel
            evidenceItems={stateQuery.data?.evidence?.items as Array<Record<string, unknown>> | undefined}
            supportedChains={stateQuery.data?.intelligence?.supported_chains}
            selectedEntityId={context.selectedEntityId}
            loading={stateQuery.isLoading}
          />
        </TabsContent>



        <TabsContent value="timeline" className="mt-4">

          <ActivityTimeline

            events={stateQuery.data?.timeline?.events}

            loading={stateQuery.isLoading}

          />

        </TabsContent>



        <TabsContent value="evidence" className="mt-4">

          <WorkspaceEvidenceSection
            items={stateQuery.data?.evidence?.items as Array<Record<string, unknown>> | undefined}
            loading={stateQuery.isLoading}
          />

        </TabsContent>



        <TabsContent value="graph" className="mt-4">

          <GraphInsightsPanel caseId={caseRef} />

        </TabsContent>



        <TabsContent value="reports" className="mt-4">
          <ReportsPanel caseRef={caseRef} />
        </TabsContent>



        <TabsContent value="tasks" className="mt-4">

          <TaskBoardPanel />

        </TabsContent>



        <TabsContent value="bookmarks" className="mt-4">

          <BookmarksPanel caseRef={caseRef} onNavigate={handleTabChange} />

        </TabsContent>



        <TabsContent value="ai" className="mt-4">

          <AiContextPanel caseRef={caseRef} investigationId={investigationId} />

        </TabsContent>



        <TabsContent value="activity" className="mt-4 space-y-4">

          <AlertCenterPanel
            notifications={Array.isArray(stateQuery.data?.notifications) ? stateQuery.data.notifications : []}
            caseRef={caseRef}
          />

          <ActivityFeedPanel
            collaborationComments={collaborationComments}
            collaborationActivity={collaborationActivity}
            fallbackTimeline={stateQuery.data?.timeline?.events}
            loading={stateQuery.isLoading}
            commentSlot={
              <>
                <div className="flex gap-2">
                  <Input
                    placeholder="Добавить комментарий…"
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && commentText.trim()) {
                        commentMutation.mutate(commentText.trim())
                      }
                    }}
                  />
                  <Button
                    size="icon"
                    disabled={!commentText.trim() || commentMutation.isPending}
                    onClick={() => commentMutation.mutate(commentText.trim())}
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
                {collaborationComments.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Комментариев пока нет</p>
                ) : (
                  <div className="space-y-3">
                    {collaborationComments.map((c) => (
                      <div key={c.id} className="text-sm border-l-2 border-muted pl-3">
                        <div className="text-foreground">{c.text}</div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {c.author} · {formatNotifTime(c.created_at)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            }
          />

        </TabsContent>

      </Tabs>



      <WorkspaceCommandPalette

        open={paletteOpen}

        onOpenChange={setPaletteOpen}

        commands={manifestQuery.data?.command_palette}

        onCommand={handlePaletteCommand}

        caseRef={caseRef}

        onSearchSelect={handleSearchSelect}

      />

      <RiskDrawerPanel
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        caseRef={caseRef}
        entityKey={context.selectedEntityId}
      />

    </div>

  )

}


