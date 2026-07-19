/** Cross-panel sync bus — graph, timeline, inspector, dock. */

import {
  DEFAULT_GRAPH_LAYERS,
  type GraphLayerToggles,
} from './fusion-graph-layers'

export type FusionDockTab =
  | 'timeline'
  | 'evidence'
  | 'blockchain'
  | 'reports'
  | 'tasks'
  | 'transactions'
  | 'osint'
  | 'wallets'

export type FusionPanelFocus =
  | 'mission'
  | 'timeline'
  | 'evidence'
  | 'reports'
  | 'mio'
  | 'graph-layers'
  | 'live-feed'

type FusionSyncState = {
  livePaused: boolean
  activeDockTab: FusionDockTab | null
  panelFocus: FusionPanelFocus | null
  graphSearchOpen: boolean
  globalSearchOpen: boolean
  graphLayers: GraphLayerToggles
  graphFocusNodeId: string | null
  graphFocusRequest: number
  centerGraphRequest: number
  executiveMode: boolean
  moneyFlowEnabled: boolean
  collaborationEnabled: boolean
}

type Listener = (state: FusionSyncState) => void

const state: FusionSyncState = {
  livePaused: false,
  activeDockTab: null,
  panelFocus: null,
  graphSearchOpen: false,
  globalSearchOpen: false,
  graphLayers: { ...DEFAULT_GRAPH_LAYERS },
  graphFocusNodeId: null,
  graphFocusRequest: 0,
  centerGraphRequest: 0,
  executiveMode: false,
  moneyFlowEnabled: true,
  collaborationEnabled: true,
}

const listeners = new Set<Listener>()

function emit() {
  listeners.forEach((fn) => fn({ ...state }))
}

export function getFusionSyncState(): FusionSyncState {
  return { ...state }
}

export function subscribeFusionSync(fn: Listener): () => void {
  listeners.add(fn)
  fn({ ...state })
  return () => listeners.delete(fn)
}

export function setLivePaused(paused: boolean) {
  state.livePaused = paused
  emit()
}

export function toggleLivePaused() {
  state.livePaused = !state.livePaused
  emit()
}

export function setActiveDockTab(tab: FusionDockTab | null) {
  state.activeDockTab = tab
  emit()
}

const DOCK_TAB_CYCLE: FusionDockTab[] = [
  'timeline',
  'evidence',
  'blockchain',
  'reports',
  'tasks',
  'wallets',
  'transactions',
  'osint',
]

export function cycleActiveDockTab() {
  const current = state.activeDockTab ?? 'timeline'
  const idx = DOCK_TAB_CYCLE.indexOf(current)
  const next = DOCK_TAB_CYCLE[(idx + 1) % DOCK_TAB_CYCLE.length]
  state.activeDockTab = next
  emit()
}

export function setPanelFocus(focus: FusionPanelFocus | null) {
  state.panelFocus = focus
  emit()
}

export function requestCenterGraph() {
  state.centerGraphRequest += 1
  emit()
}

export function setGraphSearchOpen(open: boolean) {
  state.graphSearchOpen = open
  emit()
}

export function setGraphLayers(partial: Partial<GraphLayerToggles>) {
  state.graphLayers = { ...state.graphLayers, ...partial }
  emit()
}

export function toggleGraphLayer(key: keyof GraphLayerToggles) {
  state.graphLayers[key] = !state.graphLayers[key]
  emit()
}

export function requestGraphNodeFocus(nodeId: string) {
  state.graphFocusNodeId = nodeId
  state.graphFocusRequest += 1
  emit()
}

export function setGlobalSearchOpen(open: boolean) {
  state.globalSearchOpen = open
  emit()
}

export function setExecutiveMode(active: boolean) {
  if (state.executiveMode === active) return
  state.executiveMode = active
  emit()
}

export function toggleExecutiveMode() {
  state.executiveMode = !state.executiveMode
  emit()
}

export function setMoneyFlowEnabled(enabled: boolean) {
  state.moneyFlowEnabled = enabled
  emit()
}

export function toggleMoneyFlow() {
  state.moneyFlowEnabled = !state.moneyFlowEnabled
  emit()
}

export function setCollaborationEnabled(enabled: boolean) {
  state.collaborationEnabled = enabled
  emit()
}

export function toggleCollaboration() {
  state.collaborationEnabled = !state.collaborationEnabled
  emit()
}
