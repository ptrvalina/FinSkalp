export const FUSION_LAYOUT_COMMAND_KEY = 'fusion-layout-command'
export const FUSION_LAYOUT_INVESTIGATION_KEY = 'fusion-layout-investigation'
export const FUSION_PANEL_PINS_KEY = 'fusion-panel-pins'

export type FusionLayoutState = {
  command?: { horizontal?: number[]; vertical?: number[] }
  investigation?: { main?: number[]; dock?: number[] }
}

export function loadFusionLayout(): FusionLayoutState {
  try {
    const command = localStorage.getItem(FUSION_LAYOUT_COMMAND_KEY)
    const investigation = localStorage.getItem(FUSION_LAYOUT_INVESTIGATION_KEY)
    return {
      command: command ? (JSON.parse(command) as FusionLayoutState['command']) : undefined,
      investigation: investigation
        ? (JSON.parse(investigation) as FusionLayoutState['investigation'])
        : undefined,
    }
  } catch {
    return {}
  }
}

export function saveFusionCommandLayout(horizontal: number[], vertical: number[]) {
  try {
    localStorage.setItem(
      FUSION_LAYOUT_COMMAND_KEY,
      JSON.stringify({ horizontal, vertical })
    )
  } catch {
    /* ignore */
  }
}

export function saveFusionInvestigationLayout(main: number[], dock: number[]) {
  try {
    localStorage.setItem(
      FUSION_LAYOUT_INVESTIGATION_KEY,
      JSON.stringify({ main, dock })
    )
  } catch {
    /* ignore */
  }
}

export function loadFusionPanelPins(): string[] {
  try {
    const raw = localStorage.getItem(FUSION_PANEL_PINS_KEY)
    if (raw) return JSON.parse(raw) as string[]
  } catch {
    /* ignore */
  }
  return []
}

export function toggleFusionPanelPin(panelId: string): string[] {
  const current = loadFusionPanelPins()
  const next = current.includes(panelId)
    ? current.filter((id) => id !== panelId)
    : [...current, panelId]
  try {
    localStorage.setItem(FUSION_PANEL_PINS_KEY, JSON.stringify(next))
  } catch {
    /* ignore */
  }
  return next
}

export const DEFAULT_COMMAND_LAYOUT = {
  horizontal: [50, 50],
  vertical: [50, 50],
}

export const DEFAULT_INVESTIGATION_LAYOUT = {
  main: [18, 58, 24],
  dock: [78, 22],
}
