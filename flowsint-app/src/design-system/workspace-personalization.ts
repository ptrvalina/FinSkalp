/** RFC-0010 Ch.18 — Workspace personalization (localStorage + API) */

const STORAGE_PREFIX = 'finskalp.workspace.personalization'

export type WorkspacePersonalization = {
  activeTab: string
  density: 'comfortable' | 'compact'
  theme: string
  panelLayout: Record<string, unknown>
  pinnedPanels: string[]
  locale: string
}

const DEFAULTS: WorkspacePersonalization = {
  activeTab: 'summary',
  density: 'comfortable',
  theme: 'system',
  panelLayout: {},
  pinnedPanels: [],
  locale: 'ru',
}

function storageKey(caseRef?: string | null) {
  return caseRef ? `${STORAGE_PREFIX}.${caseRef}` : STORAGE_PREFIX
}

export function loadWorkspacePersonalization(caseRef?: string | null): WorkspacePersonalization {
  try {
    const raw = localStorage.getItem(storageKey(caseRef))
    if (!raw) return { ...DEFAULTS }
    return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULTS }
  }
}

export function saveWorkspacePersonalization(
  partial: Partial<WorkspacePersonalization>,
  caseRef?: string | null
) {
  const current = loadWorkspacePersonalization(caseRef)
  const next = { ...current, ...partial }
  try {
    localStorage.setItem(storageKey(caseRef), JSON.stringify(next))
  } catch {
    /* ignore */
  }
  return next
}

export function personalizationToApiPayload(prefs: WorkspacePersonalization) {
  return {
    active_tab: prefs.activeTab,
    density: prefs.density,
    theme: prefs.theme,
    panel_layout: prefs.panelLayout,
    pinned_panels: prefs.pinnedPanels,
    locale: prefs.locale,
  }
}

export function apiPayloadToPersonalization(payload: Record<string, unknown>): WorkspacePersonalization {
  return {
    activeTab: String(payload.active_tab ?? DEFAULTS.activeTab),
    density: (payload.density as WorkspacePersonalization['density']) ?? DEFAULTS.density,
    theme: String(payload.theme ?? DEFAULTS.theme),
    panelLayout: (payload.panel_layout as Record<string, unknown>) ?? {},
    pinnedPanels: Array.isArray(payload.pinned_panels) ? (payload.pinned_panels as string[]) : [],
    locale: String(payload.locale ?? DEFAULTS.locale),
  }
}
