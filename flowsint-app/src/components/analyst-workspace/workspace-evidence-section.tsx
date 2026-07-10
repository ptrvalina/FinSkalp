import { useMemo, useState } from 'react'

import { EnterprisePanel, EvidenceRow } from '@/components/enterprise/enterprise-ui'
import { Skeleton } from '@/components/ui/skeleton'

import { EvidenceDrawer, type WorkspaceEvidenceItem } from './evidence-drawer'

type Props = {
  items?: Array<Record<string, unknown>>
  loading?: boolean
}

function mapItems(raw?: Array<Record<string, unknown>>): WorkspaceEvidenceItem[] {
  if (!raw?.length) {
    return [
      {
        id: 'EV-2026-0000001101',
        type: 'Case memo',
        source: 'Analyst workspace',
        checksum: 'e7f31a7cb124aff0193392beef4451bc0012aabc',
        receivedAt: '09 Jul 2026 13:58',
        verified: 'verified',
      },
    ]
  }
  return raw.slice(0, 20).map((item, index) => ({
    id: String(item.id ?? `EV-2026-00000011${index}`),
    type: String(item.kind ?? item.type ?? 'Evidence item'),
    source: String(item.source ?? 'Workspace'),
    checksum: String(item.checksum ?? item.sha256 ?? `checksum-${index}`),
    receivedAt: String(item.received_at ?? item.created_at ?? 'Recent'),
    verified: (item.status === 'verified'
      ? 'verified'
      : item.status === 'review'
        ? 'review'
        : 'pending') as WorkspaceEvidenceItem['verified'],
  }))
}

export function WorkspaceEvidenceSection({ items, loading }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const mapped = useMemo(() => mapItems(items), [items])

  return (
    <>
      <EnterprisePanel
        title="Evidence"
        description="Click a row to open ECCF evidence drawer (audit, timeline, integrity)."
      >
        {loading ? (
          <Skeleton className="h-32 w-full" />
        ) : (
          <div className="space-y-1">
            {mapped.map((item) => (
              <button
                key={item.id}
                type="button"
                className="w-full text-left rounded-sm hover:bg-muted/40 transition-colors"
                onClick={() => setSelectedId(item.id)}
              >
                <EvidenceRow item={item} />
              </button>
            ))}
          </div>
        )}
      </EnterprisePanel>
      <EvidenceDrawer evidenceId={selectedId} onClose={() => setSelectedId(null)} />
    </>
  )
}
