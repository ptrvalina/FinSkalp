import { useCallback, useEffect, useState } from 'react'

import {
  floatPositionFromSession,
  loadCaseSession,
  mergeCaseSession,
  mergeFloatPosition,
  recordCaseAction,
  saveGpuCamera,
  type FloatPanelPosition,
  type FusionCaseSessionState,
  type GpuCameraState,
} from './fusion-case-session'

export function useFusionCaseSession(caseRef: string | null | undefined) {
  const [session, setSession] = useState<FusionCaseSessionState>(() =>
    caseRef ? loadCaseSession(caseRef) : {}
  )

  useEffect(() => {
    if (caseRef) setSession(loadCaseSession(caseRef))
  }, [caseRef])

  const update = useCallback(
    (partial: Partial<FusionCaseSessionState>) => {
      if (!caseRef) return session
      const next = mergeCaseSession(caseRef, partial)
      setSession(next)
      return next
    },
    [caseRef, session]
  )

  const recordAction = useCallback(
    (action: string) => {
      if (caseRef) {
        recordCaseAction(caseRef, action)
        setSession(loadCaseSession(caseRef))
      }
    },
    [caseRef]
  )

  const getFloatPosition = useCallback(
    (panelId: string): FloatPanelPosition | undefined =>
      caseRef ? floatPositionFromSession(loadCaseSession(caseRef), panelId) : undefined,
    [caseRef]
  )

  const setFloatPosition = useCallback(
    (panelId: string, position: FloatPanelPosition) => {
      if (!caseRef) return
      const next = mergeFloatPosition(caseRef, panelId, position)
      setSession(next)
    },
    [caseRef]
  )

  const persistGpuCamera = useCallback(
    (camera: GpuCameraState) => {
      if (!caseRef) return
      saveGpuCamera(caseRef, camera)
      setSession(loadCaseSession(caseRef))
    },
    [caseRef]
  )

  return {
    session,
    update,
    recordAction,
    getFloatPosition,
    setFloatPosition,
    persistGpuCamera,
  }
}
