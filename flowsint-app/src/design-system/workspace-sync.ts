/** RFC-0010 Ch.15 — Multi-window sync via BroadcastChannel */

import { useCallback, useEffect, useRef } from 'react'

export const WORKSPACE_SYNC_CHANNEL = 'finskalp.workspace.v1'

export type WorkspaceSyncPayload = {
  selectedEntityId: string | null
  caseRef: string | null
  activeTab: string
  filters: Record<string, unknown>
  sourceWindowId: string
}

const windowId =
  typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `win-${Date.now()}`

export function createWorkspaceSync(handlers: {
  onRemoteUpdate: (payload: Omit<WorkspaceSyncPayload, 'sourceWindowId'>) => void
}) {
  const channel =
    typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel(WORKSPACE_SYNC_CHANNEL) : null

  const broadcast = (partial: Partial<Omit<WorkspaceSyncPayload, 'sourceWindowId'>>) => {
    if (!channel) return
    channel.postMessage({
      selectedEntityId: partial.selectedEntityId ?? null,
      caseRef: partial.caseRef ?? null,
      activeTab: partial.activeTab ?? 'summary',
      filters: partial.filters ?? {},
      sourceWindowId: windowId,
      ...partial,
    } satisfies WorkspaceSyncPayload)
  }

  const onMessage = (ev: MessageEvent<WorkspaceSyncPayload>) => {
    const data = ev.data
    if (!data || data.sourceWindowId === windowId) return
    handlers.onRemoteUpdate({
      selectedEntityId: data.selectedEntityId,
      caseRef: data.caseRef,
      activeTab: data.activeTab,
      filters: data.filters,
    })
  }

  channel?.addEventListener('message', onMessage)

  return {
    broadcast,
    close: () => {
      channel?.removeEventListener('message', onMessage)
      channel?.close()
    },
  }
}

export function useWorkspaceSync(opts: {
  selectedEntityId: string | null
  caseRef: string | null
  activeTab: string
  filters: Record<string, unknown>
  onRemoteUpdate: (payload: Omit<WorkspaceSyncPayload, 'sourceWindowId'>) => void
}) {
  const syncRef = useRef<ReturnType<typeof createWorkspaceSync> | null>(null)
  const optsRef = useRef(opts)
  optsRef.current = opts

  useEffect(() => {
    syncRef.current = createWorkspaceSync({
      onRemoteUpdate: (payload) => optsRef.current.onRemoteUpdate(payload),
    })
    return () => syncRef.current?.close()
  }, [])

  const broadcast = useCallback((partial: Partial<Omit<WorkspaceSyncPayload, 'sourceWindowId'>>) => {
    syncRef.current?.broadcast(partial)
  }, [])

  useEffect(() => {
    broadcast({
      selectedEntityId: opts.selectedEntityId,
      caseRef: opts.caseRef,
      activeTab: opts.activeTab,
      filters: opts.filters,
    })
  }, [broadcast, opts.selectedEntityId, opts.caseRef, opts.activeTab, opts.filters])

  return { broadcast }
}
