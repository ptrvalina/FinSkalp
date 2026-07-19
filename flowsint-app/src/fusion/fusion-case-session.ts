/** Per-case investigation session — localStorage without API calls (U1) */

import type { GraphLayerToggles } from './fusion-graph-layers'
import { DEFAULT_GRAPH_LAYERS } from './fusion-graph-layers'
import type { FusionDockTab } from './fusion-sync-bus'
import type { InvestigationSeed } from './fusion-investigation-seed'

export type PipelineStatus = 'pending' | 'running' | 'done' | 'error'
export type PipelinePhase = 'collectors' | 'graph' | 'kyt' | 'done'

export type FusionCaseSessionState = {
  selectedNodeId?: string | null
  selectedTimelineEventId?: string | null
  selectedEvidenceId?: string | null
  replayIndex?: number
  hopLensMaxDepth?: number | null
  dockTab?: FusionDockTab | string
  leftTab?: 'timeline' | 'hypotheses'
  graphLayers?: GraphLayerToggles
  moneyFlowEnabled?: boolean
  livePaused?: boolean
  reactFlowCamera?: { x: number; y: number; zoom: number }
  gpuCamera?: { x: number; y: number; ratio: number }
  floatPositions?: Record<string, { x: number; y: number }>
  lastAction?: string
  lastActionAt?: number
  investigationSeed?: InvestigationSeed
  investigationWallet?: { address: string; chain?: string }
  enabledCollectors?: string[]
  lastKyt?: {
    address: string
    chain?: string
    score: number
    level: string
    at: number
  }
  pipelineStatus?: PipelineStatus
  pipelinePhase?: PipelinePhase
  pipelineError?: string
  pipelineCollectorStatus?: Record<string, string>
  pipelineCollectorsRun?: string[]
}

export function caseSessionKey(caseRef: string): string {
  return `finskalp-case-session-${caseRef}`
}

export function loadCaseSession(caseRef: string): FusionCaseSessionState {
  try {
    const raw = localStorage.getItem(caseSessionKey(caseRef))
    if (!raw) return {}
    return JSON.parse(raw) as FusionCaseSessionState
  } catch {
    return {}
  }
}

export function saveCaseSession(caseRef: string, state: FusionCaseSessionState): void {
  try {
    localStorage.setItem(caseSessionKey(caseRef), JSON.stringify(state))
  } catch {
    /* ignore quota */
  }
}

export function mergeCaseSession(
  caseRef: string,
  partial: Partial<FusionCaseSessionState>
): FusionCaseSessionState {
  const prev = loadCaseSession(caseRef)
  const next = { ...prev, ...partial }
  saveCaseSession(caseRef, next)
  return next
}

export function recordCaseAction(caseRef: string, action: string): void {
  mergeCaseSession(caseRef, { lastAction: action, lastActionAt: Date.now() })
}

export function defaultGraphLayersFromSession(
  session: FusionCaseSessionState
): GraphLayerToggles {
  return session.graphLayers ?? { ...DEFAULT_GRAPH_LAYERS }
}

export type GpuCameraState = NonNullable<FusionCaseSessionState['gpuCamera']>
export type FloatPanelPosition = { x: number; y: number }

export function floatPositionFromSession(
  session: FusionCaseSessionState,
  panelId: string
): FloatPanelPosition | undefined {
  return session.floatPositions?.[panelId]
}

export function mergeFloatPosition(
  caseRef: string,
  panelId: string,
  position: FloatPanelPosition
): FusionCaseSessionState {
  const prev = loadCaseSession(caseRef)
  return mergeCaseSession(caseRef, {
    floatPositions: { ...prev.floatPositions, [panelId]: position },
  })
}

export function saveGpuCamera(caseRef: string, camera: GpuCameraState): void {
  mergeCaseSession(caseRef, { gpuCamera: camera })
}

export function gpuCameraFromSession(caseRef: string): GpuCameraState | undefined {
  return loadCaseSession(caseRef).gpuCamera
}
