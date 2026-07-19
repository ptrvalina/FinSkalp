import { useCallback, useEffect, useRef } from 'react'

export type FusionSyncState = {
  selectedNodeId: string | null
  replayIndex: number
}

export type FusionSyncMessage =
  | { type: 'state'; source: string; state: FusionSyncState }
  | { type: 'ping'; source: string }

function channelName(caseRef: string) {
  return `finskalp-fusion-${caseRef}`
}

export function useFusionBroadcastSync(
  caseRef: string | undefined,
  state: FusionSyncState,
  onRemoteState: (state: FusionSyncState) => void
) {
  const sourceId = useRef(
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `fusion-${Date.now()}`
  )
  const applyingRemote = useRef(false)
  const onRemoteStateRef = useRef(onRemoteState)
  onRemoteStateRef.current = onRemoteState

  const broadcast = useCallback(
    (next: FusionSyncState) => {
      if (!caseRef || applyingRemote.current) return
      try {
        const channel = new BroadcastChannel(channelName(caseRef))
        const message: FusionSyncMessage = {
          type: 'state',
          source: sourceId.current,
          state: next,
        }
        channel.postMessage(message)
        channel.close()
      } catch {
        /* BroadcastChannel unavailable */
      }
    },
    [caseRef]
  )

  useEffect(() => {
    if (!caseRef) return
    broadcast(state)
  }, [caseRef, state.selectedNodeId, state.replayIndex, broadcast])

  useEffect(() => {
    if (!caseRef) return
    let channel: BroadcastChannel | null = null
    try {
      channel = new BroadcastChannel(channelName(caseRef))
    } catch {
      return
    }

    const lastRemote = { selectedNodeId: null as string | null, replayIndex: -1 }
    const handler = (event: MessageEvent<FusionSyncMessage>) => {
      const data = event.data
      if (!data || data.source === sourceId.current) return
      if (data.type === 'state') {
        const next = data.state
        if (
          next.selectedNodeId === lastRemote.selectedNodeId &&
          next.replayIndex === lastRemote.replayIndex
        ) {
          return
        }
        lastRemote.selectedNodeId = next.selectedNodeId
        lastRemote.replayIndex = next.replayIndex
        applyingRemote.current = true
        onRemoteStateRef.current(next)
        queueMicrotask(() => {
          applyingRemote.current = false
        })
      }
    }

    channel.addEventListener('message', handler)
    channel.postMessage({ type: 'ping', source: sourceId.current })

    return () => {
      channel?.removeEventListener('message', handler)
      channel?.close()
    }
  }, [caseRef])

  return { broadcast, sourceId: sourceId.current }
}
