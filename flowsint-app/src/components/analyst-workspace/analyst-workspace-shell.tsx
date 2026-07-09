import { useCallback, useEffect, useMemo, useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { Link } from '@tanstack/react-router'

import {

  Activity,

  Bell,

  Briefcase,

  ExternalLink,

  FileText,

  GitBranch,

  LayoutDashboard,

  MessageSquare,

  Send,

  Wallet,

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

import { EvidenceSection } from '@/components/dashboard/investigation/evidence-section'

import { Badge } from '@/components/ui/badge'

import { Button } from '@/components/ui/button'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import { Input } from '@/components/ui/input'

import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

import { Skeleton } from '@/components/ui/skeleton'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { useTheme } from '@/components/theme-provider'

import { WorkspaceCommandPalette } from './workspace-command-palette'



const TAB_LABELS: Record<string, string> = {

  summary: 'Сводка',

  entities: 'Сущности',

  wallets: 'Кошельки',

  timeline: 'Хронология',

  evidence: 'Доказательства',

  graph: 'Граф',

  reports: 'Отчёты',

  activity: 'Активность',

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

      }

    }

    window.addEventListener('keydown', onKeyDown)

    return () => window.removeEventListener('keydown', onKeyDown)

  }, [])



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

      <Card>

        <CardHeader className="pb-3">

          <div className="flex items-start justify-between gap-4">

            <div>

              <CardTitle className="text-base flex items-center gap-2">

                <LayoutDashboard className="w-4 h-4" />

                Рабочее пространство аналитика

              </CardTitle>

              <CardDescription className="font-mono mt-1">{caseRef}</CardDescription>

              <p className="text-xs text-muted-foreground mt-1">{investigationName}</p>

            </div>

            <div className="flex flex-wrap gap-2 items-center">

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

                Команды (Ctrl+K)

              </Button>

              <Button size="sm" variant="outline" asChild>

                <Link to="/dashboard/compliance">

                  Комплаенс

                  <ExternalLink className="w-3.5 h-3.5 ml-1.5" />

                </Link>

              </Button>

            </div>

          </div>

        </CardHeader>

        <CardContent className="flex flex-wrap gap-2">

          <Badge variant="outline">RFC-0010</Badge>

          {workflow?.workflow_status ? (

            <Badge variant="secondary">{String(workflow.workflow_status)}</Badge>

          ) : null}

          {counts ? (

            <>

              <Badge variant="outline">{counts.evidence} доказательств</Badge>

              <Badge variant="outline">{counts.timeline} событий</Badge>

            </>

          ) : null}

          {stateQuery.data?.intelligence ? (

            <Badge variant="outline">

              {stateQuery.data.intelligence.engines_count} движков

            </Badge>

          ) : null}

          {stateQuery.data?.latency_ms != null ? (

            <Badge variant="outline" className="font-mono text-xs">

              {stateQuery.data.latency_ms} мс

            </Badge>

          ) : null}

        </CardContent>

      </Card>



      <Tabs value={activeTab} onValueChange={handleTabChange}>

        <TabsList className="flex flex-wrap h-auto gap-1">

          {tabs.map((tab) => (

            <TabsTrigger key={tab} value={tab} className="text-xs sm:text-sm">

              {manifestQuery.data?.workspace_tabs_ru?.[tab] ?? TAB_LABELS[tab] ?? tab}

            </TabsTrigger>

          ))}

        </TabsList>



        <TabsContent value="summary" className="mt-4">

          <Card>

            <CardHeader>

              <CardTitle className="text-sm flex items-center gap-2">

                <Briefcase className="w-4 h-4" />

                Сводка расследования

              </CardTitle>

            </CardHeader>

            <CardContent className="text-sm text-muted-foreground space-y-2">

              <p>Расследование: {investigationName}</p>

              <p>Кейс: {caseRef}</p>

              {stateQuery.data?.intelligence?.rule_ru ? (
                <p className="text-xs">{stateQuery.data.intelligence.rule_ru}</p>
              ) : null}
              {workflowRecsQuery.data?.recommendations?.length ? (
                <div className="pt-2 space-y-1">
                  <p className="text-xs font-medium text-foreground">Рекомендации (RFC-0011)</p>
                  {workflowRecsQuery.data.recommendations.slice(0, 3).map((rec) => (
                    <p key={rec.id} className="text-xs">
                      {rec.action_ru} — {rec.explanation_ru}
                    </p>
                  ))}
                </div>
              ) : null}

            </CardContent>

          </Card>

        </TabsContent>



        <TabsContent value="entities" className="mt-4">

          <Card>

            <CardContent className="pt-6 text-sm text-muted-foreground">

              Сущности графа знаний — выберите сущность в графе или через поиск (Ctrl+K).

              {context.selectedEntityId ? (

                <p className="mt-2 font-mono text-foreground">

                  Выбрано: {context.selectedEntityId}

                </p>

              ) : null}

            </CardContent>

          </Card>

        </TabsContent>



        <TabsContent value="wallets" className="mt-4">

          <Card>

            <CardContent className="pt-6 text-sm text-muted-foreground flex items-center gap-2">

              <Wallet className="w-4 h-4" />

              Обозреватель кошельков — цепочки:{' '}

              {(stateQuery.data?.intelligence?.supported_chains ?? []).join(', ') || '—'}

            </CardContent>

          </Card>

        </TabsContent>



        <TabsContent value="timeline" className="mt-4">

          <ActivityTimeline

            events={stateQuery.data?.timeline?.events}

            loading={stateQuery.isLoading}

          />

        </TabsContent>



        <TabsContent value="evidence" className="mt-4">

          <EvidenceSection

            items={stateQuery.data?.evidence?.items}

            loading={stateQuery.isLoading}

          />

        </TabsContent>



        <TabsContent value="graph" className="mt-4">

          <Card>

            <CardContent className="pt-6 text-sm text-muted-foreground flex items-center gap-2">

              <GitBranch className="w-4 h-4" />

              Граф связей — откройте{' '}

              <Link to="/dashboard/compliance" className="text-primary underline">

                комплаенс

              </Link>{' '}

              для полного графа доказательств.

            </CardContent>

          </Card>

        </TabsContent>



        <TabsContent value="reports" className="mt-4">

          <Card>

            <CardContent className="pt-6 text-sm text-muted-foreground flex items-center gap-2">

              <FileText className="w-4 h-4" />

              Отчёты RFC-0005 — доступны через API комплаенса для связанного кейса.

            </CardContent>

          </Card>

        </TabsContent>



        <TabsContent value="activity" className="mt-4 space-y-4">

          <Card>

            <CardHeader>

              <CardTitle className="text-sm flex items-center gap-2">

                <MessageSquare className="w-4 h-4" />

                Комментарии ({collaborationComments.length})

              </CardTitle>

            </CardHeader>

            <CardContent className="space-y-4">

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

            </CardContent>

          </Card>

          <Card>

            <CardHeader>

              <CardTitle className="text-sm flex items-center gap-2">

                <Activity className="w-4 h-4" />

                Лента активности

              </CardTitle>

            </CardHeader>

            <CardContent>

              <ActivityTimeline

                events={

                  collaborationActivity.length > 0

                    ? collaborationActivity.map((e) => ({

                        id: e.id,

                        event_type:

                          e.event_type === 'comment' || e.event_type === 'collaboration_comment'

                            ? `Комментарий: ${(e.payload?.text as string)?.slice(0, 80) ?? ''}`

                            : e.event_type,

                        occurred_at: e.occurred_at,

                        actor: e.actor,

                        payload: e.payload,

                      }))

                    : stateQuery.data?.timeline?.events

                }

                loading={stateQuery.isLoading}

              />

            </CardContent>

          </Card>

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

    </div>

  )

}


