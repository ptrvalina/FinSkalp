import { useCallback, useMemo } from 'react'

import {
  loadWorkspacePersonalization,
  saveWorkspacePersonalization,
  personalizationToApiPayload,
} from '@/design-system'
import { complianceService } from '@/api/compliance-service'
import { EnterprisePanel } from '@/components/enterprise/enterprise-ui'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Bookmark, BookmarkCheck } from 'lucide-react'

const PINNABLE: Array<{ id: string; label: string }> = [
  { id: 'summary', label: 'Сводка' },
  { id: 'timeline', label: 'Хронология' },
  { id: 'evidence', label: 'Доказательства' },
  { id: 'graph', label: 'Граф' },
  { id: 'tasks', label: 'Задачи' },
  { id: 'ai', label: 'AI Context' },
  { id: 'activity', label: 'Активность' },
]

type Props = {
  caseRef: string
  onNavigate?: (tab: string) => void
}

export function BookmarksPanel({ caseRef, onNavigate }: Props) {
  const prefs = useMemo(() => loadWorkspacePersonalization(caseRef), [caseRef])
  const pinned = new Set(prefs.pinnedPanels)

  const toggle = useCallback(
    (panelId: string) => {
      const next = new Set(pinned)
      if (next.has(panelId)) next.delete(panelId)
      else next.add(panelId)
      const updated = saveWorkspacePersonalization(
        { pinnedPanels: Array.from(next) },
        caseRef
      )
      complianceService
        .saveAnalystWorkspacePersonalization(personalizationToApiPayload(updated))
        .catch(() => undefined)
    },
    [caseRef, pinned]
  )

  return (
    <EnterprisePanel title="Bookmarks" description="Pinned panels — workspace personalization API">
      <div className="flex flex-wrap gap-2">
        {PINNABLE.map((item) => {
          const isPinned = pinned.has(item.id)
          return (
            <Button
              key={item.id}
              size="sm"
              variant={isPinned ? 'default' : 'outline'}
              className="gap-1"
              onClick={() => toggle(item.id)}
              onDoubleClick={() => onNavigate?.(item.id)}
            >
              {isPinned ? (
                <BookmarkCheck className="h-3.5 w-3.5" />
              ) : (
                <Bookmark className="h-3.5 w-3.5" />
              )}
              {item.label}
            </Button>
          )
        })}
      </div>
      {pinned.size ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {Array.from(pinned).map((id) => (
            <Badge
              key={id}
              variant="secondary"
              className="cursor-pointer"
              onClick={() => onNavigate?.(id)}
            >
              {PINNABLE.find((p) => p.id === id)?.label ?? id}
            </Badge>
          ))}
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground">Нет закладок. Нажмите, чтобы закрепить панель.</p>
      )}
    </EnterprisePanel>
  )
}
