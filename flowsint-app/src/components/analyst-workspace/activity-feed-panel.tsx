import type { ReactNode } from 'react'

import { ActivityTimeline } from '@/components/dashboard/investigation/activity-timeline'
import { EnterprisePanel } from '@/components/enterprise/enterprise-ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity } from 'lucide-react'

type TimelineEvent = {
  id: string
  event_type: string
  occurred_at?: string
  actor?: string
  payload?: Record<string, unknown>
}

type Comment = {
  id: string
  text: string
  author?: string
  created_at?: string
}

type Props = {
  collaborationComments: Comment[]
  collaborationActivity: TimelineEvent[]
  fallbackTimeline?: TimelineEvent[]
  loading?: boolean
  commentSlot?: ReactNode
}

function formatNotifTime(iso?: string) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('ru-RU')
  } catch {
    return iso
  }
}

export function ActivityFeedPanel({
  collaborationComments,
  collaborationActivity,
  fallbackTimeline,
  loading,
  commentSlot,
}: Props) {
  const feedEvents =
    collaborationActivity.length > 0
      ? collaborationActivity.map((e) => ({
          id: e.id,
          event_type:
            e.event_type === 'comment' || e.event_type === 'collaboration_comment'
              ? `Комментарий: ${String(e.payload?.text ?? '').slice(0, 80)}`
              : e.event_type,
          occurred_at: e.occurred_at ?? '',
          actor: e.actor,
          payload: e.payload,
        }))
      : fallbackTimeline?.map((e) => ({
          ...e,
          occurred_at: e.occurred_at ?? '',
        }))

  return (
    <div className="space-y-4">
      {commentSlot ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Комментарии ({collaborationComments.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">{commentSlot}</CardContent>
        </Card>
      ) : null}

      <EnterprisePanel title="Activity Feed" description="Collaboration + investigation timeline">
        <div className="flex items-center gap-2 text-sm font-medium mb-3">
          <Activity className="h-4 w-4" />
          Лента активности
        </div>
        {collaborationComments.length > 0 && !commentSlot ? (
          <div className="mb-4 space-y-2">
            {collaborationComments.map((c) => (
              <div key={c.id} className="text-sm border-l-2 border-muted pl-3">
                <div>{c.text}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {c.author} · {formatNotifTime(c.created_at)}
                </div>
              </div>
            ))}
          </div>
        ) : null}
        <ActivityTimeline events={feedEvents} loading={loading} />
      </EnterprisePanel>
    </div>
  )
}
