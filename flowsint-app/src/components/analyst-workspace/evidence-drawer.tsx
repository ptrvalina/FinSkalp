import { useQuery } from '@tanstack/react-query'

import { complianceService } from '@/api/compliance-service'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { ActivityTimeline } from '@/components/dashboard/investigation/activity-timeline'

export type WorkspaceEvidenceItem = {
  id: string
  type: string
  source: string
  checksum: string
  receivedAt: string
  verified: 'verified' | 'pending' | 'review'
}

type Props = {
  evidenceId: string | null
  onClose: () => void
}

export function EvidenceDrawer({ evidenceId, onClose }: Props) {
  const open = Boolean(evidenceId)

  const recordQuery = useQuery({
    queryKey: ['eccf', 'record', evidenceId],
    queryFn: () => complianceService.getEccfEvidence(evidenceId!),
    enabled: open,
  })

  const auditQuery = useQuery({
    queryKey: ['eccf', 'audit', evidenceId],
    queryFn: () => complianceService.getEccfAuditTrail(evidenceId!),
    enabled: open,
  })

  const timelineQuery = useQuery({
    queryKey: ['eccf', 'timeline', evidenceId],
    queryFn: () => complianceService.getEccfTimeline(evidenceId!),
    enabled: open,
  })

  const verifyQuery = useQuery({
    queryKey: ['eccf', 'verify', evidenceId],
    queryFn: () => complianceService.verifyEccfIntegrity(evidenceId!),
    enabled: open,
  })

  const record = recordQuery.data?.record

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="font-mono text-sm">{evidenceId}</SheetTitle>
          <SheetDescription>ECCF chain of custody, audit trail, integrity</SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-4 text-sm">
          {recordQuery.isLoading ? <Skeleton className="h-20 w-full" /> : null}
          {record ? (
            <div className="space-y-1 rounded-md border p-3">
              <p>
                <span className="text-muted-foreground">Entity:</span>{' '}
                {String(record.entity_value ?? '—')}
              </p>
              <p>
                <span className="text-muted-foreground">Source:</span>{' '}
                {String(record.source_type ?? '—')}
              </p>
              <p className="font-mono text-xs break-all">
                {String(record.content_hash ?? '')}
              </p>
              <Badge variant="outline">{String(record.lifecycle ?? 'registered')}</Badge>
            </div>
          ) : null}

          {verifyQuery.data ? (
            <Badge variant={verifyQuery.data.ok ? 'default' : 'destructive'}>
              Integrity {verifyQuery.data.ok ? 'OK' : 'FAILED'}
            </Badge>
          ) : null}

          {auditQuery.data?.entries?.length ? (
            <div>
              <p className="text-xs font-medium mb-2">Audit trail ({auditQuery.data.count})</p>
              <ul className="space-y-1 text-xs text-muted-foreground">
                {auditQuery.data.entries.map((e, i) => (
                  <li key={i}>
                    {e.action} · {e.actor} · {e.timestamp}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {timelineQuery.data?.events?.length ? (
            <ActivityTimeline
              events={timelineQuery.data.events.map((e, i) => ({
                id: `eccf-${i}`,
                event_type: e.label || e.event_type,
                occurred_at: e.timestamp,
              }))}
            />
          ) : null}

          <Button size="sm" variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
