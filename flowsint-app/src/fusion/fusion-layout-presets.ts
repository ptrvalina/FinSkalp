import {
  FUSION_LAYOUT_COMMAND_KEY,
  FUSION_LAYOUT_INVESTIGATION_KEY,
  type FusionLayoutState,
} from './fusion-layout-storage'

export const FUSION_LAYOUT_PRESETS_KEY = 'fusion-layout-presets-v1'
export const FUSION_SHARED_QUEUE_SIZE_KEY = 'fusion-shared-queue-size-v1'
export const FUSION_GPU_GRAPH_KEY = 'fusion-gpu-graph-enabled'

export type LayoutPreset = {
  id: string
  name: string
  savedAt: string
  command?: FusionLayoutState['command']
  investigation?: FusionLayoutState['investigation']
  queueSize?: number
}

export function loadLayoutPresets(): LayoutPreset[] {
  try {
    const raw = localStorage.getItem(FUSION_LAYOUT_PRESETS_KEY)
    if (raw) return JSON.parse(raw) as LayoutPreset[]
  } catch {
    /* ignore */
  }
  return []
}

export function saveLayoutPreset(name: string): LayoutPreset {
  const presets = loadLayoutPresets()
  const commandRaw = localStorage.getItem(FUSION_LAYOUT_COMMAND_KEY)
  const invRaw = localStorage.getItem(FUSION_LAYOUT_INVESTIGATION_KEY)
  const queueRaw = localStorage.getItem(FUSION_SHARED_QUEUE_SIZE_KEY)
  const preset: LayoutPreset = {
    id: `preset-${Date.now()}`,
    name,
    savedAt: new Date().toISOString(),
    command: commandRaw ? JSON.parse(commandRaw) : undefined,
    investigation: invRaw ? JSON.parse(invRaw) : undefined,
    queueSize: queueRaw ? Number(queueRaw) : undefined,
  }
  presets.unshift(preset)
  localStorage.setItem(FUSION_LAYOUT_PRESETS_KEY, JSON.stringify(presets.slice(0, 12)))
  return preset
}

export function applyLayoutPreset(preset: LayoutPreset) {
  if (preset.command) {
    localStorage.setItem(FUSION_LAYOUT_COMMAND_KEY, JSON.stringify(preset.command))
  }
  if (preset.investigation) {
    localStorage.setItem(FUSION_LAYOUT_INVESTIGATION_KEY, JSON.stringify(preset.investigation))
  }
  if (preset.queueSize != null) {
    localStorage.setItem(FUSION_SHARED_QUEUE_SIZE_KEY, String(preset.queueSize))
  }
  window.location.reload()
}

export function deleteLayoutPreset(id: string) {
  const next = loadLayoutPresets().filter((p) => p.id !== id)
  localStorage.setItem(FUSION_LAYOUT_PRESETS_KEY, JSON.stringify(next))
}

export function loadSharedQueueSize(defaultSize = 20): number {
  try {
    const raw = localStorage.getItem(FUSION_SHARED_QUEUE_SIZE_KEY)
    if (raw) {
      const n = Number(raw)
      if (!Number.isNaN(n) && n >= 10 && n <= 35) return n
    }
  } catch {
    /* ignore */
  }
  return defaultSize
}

export function saveSharedQueueSize(size: number) {
  try {
    localStorage.setItem(FUSION_SHARED_QUEUE_SIZE_KEY, String(Math.round(size)))
  } catch {
    /* ignore */
  }
}

export function isGpuGraphEnabled(): boolean {
  try {
    return localStorage.getItem(FUSION_GPU_GRAPH_KEY) === '1'
  } catch {
    return false
  }
}

export function setGpuGraphEnabled(enabled: boolean) {
  try {
    localStorage.setItem(FUSION_GPU_GRAPH_KEY, enabled ? '1' : '0')
  } catch {
    /* ignore */
  }
}
