import { useQuery } from '@tanstack/react-query'

import { complianceService } from '@/api/compliance-service'
import { EnterprisePanel } from '@/components/enterprise/enterprise-ui'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Bell } from 'lucide-react'

type Props = {
  notifications?: Array<Record<string, unknown>>
  caseRef?: string
}

type InboxItem = {
  id: string
  alert_code?: string
  case_ref?: string
  priority?: string
  workflow_status?: string
  title_ru?: string
}

export function AlertCenterPanel({ notifications = [], caseRef }: Props) {
  const inboxQuery = useQuery({
    queryKey: ['compliance', 'demo-inbox', caseRef],
    queryFn: () => complianceService.listDemoInbox(),
    retry: false,
  })

  const inbox = (inboxQuery.data ?? []) as InboxItem[]
  const filteredInbox = caseRef
    ? inbox.filter((a) => !('case_ref' in a) || (a as { case_ref?: string }).case_ref === caseRef)
    : inbox

  return (
    <EnterprisePanel
      title="Alert Center"
      description="Workspace notifications + demo inbox bridge."
    >
      <div className="space-y-6">
        <section>
          <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
            <Bell className="w-4 h-4" />
            Уведомления workspace
          </h4>
          {notifications.length === 0 ? (
            <p className="text-sm text-muted-foreground">Нет активных уведомлений.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {notifications.slice(0, 10).map((n, i) => (
                <li key={String(n.id ?? i)} className="rounded border p-2">
                  <div className="font-medium">{String(n.title ?? n.type ?? 'Уведомление')}</div>
                  <div className="text-muted-foreground text-xs">{String(n.message ?? '')}</div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h4 className="text-sm font-medium mb-2">Inbox (демо API)</h4>
          {inboxQuery.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : inboxQuery.isError ? (
            <p className="text-sm text-muted-foreground">Inbox недоступен на этом API.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {filteredInbox.slice(0, 8).map((a) => (
                <li key={a.id} className="flex items-center justify-between rounded border p-2">
                  <span>{a.title_ru ?? a.alert_code ?? a.id}</span>
                  <div className="flex gap-1">
                    {a.priority ? <Badge variant="outline">{a.priority}</Badge> : null}
                    {a.workflow_status ? <Badge variant="secondary">{a.workflow_status}</Badge> : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </EnterprisePanel>
  )
}
