/** RFC-0008 Enterprise Design System manifest */

export const DESIGN_PRINCIPLES = [
  'investigation_first',
  'information_density',
  'progressive_disclosure',
  'explainability',
  'context_preservation',
] as const

export const DESIGN_PRINCIPLES_RU: Record<(typeof DESIGN_PRINCIPLES)[number], string> = {
  investigation_first: 'Investigation First — всё в контексте расследования',
  information_density: 'Information Density — много данных без шума',
  progressive_disclosure: 'Progressive Disclosure — детали по запросу',
  explainability: 'Explainability — любой показатель объясним',
  context_preservation: 'Context Preservation — фильтры и сущность сохраняются',
}

export const THEMES = ['light', 'dark', 'high-contrast'] as const

export const SPACING_SCALE = [4, 8, 16, 24, 32, 48] as const

export const TYPOGRAPHY_SCALE = [
  'h1',
  'h2',
  'h3',
  'h4',
  'body-lg',
  'body',
  'caption',
  'label',
] as const

export const SEMANTIC_COLORS = ['success', 'warning', 'error', 'info'] as const

export const RISK_COLORS = ['low', 'medium', 'high', 'critical'] as const

export const GRAPH_ENTITY_COLORS = [
  'wallet',
  'person',
  'company',
  'exchange',
  'contract',
  'document',
  'evidence',
  'investigation',
] as const

export const REQUIRED_COMPONENTS = {
  navigation: ['Sidebar', 'TopBar', 'Breadcrumbs', 'CommandPalette'],
  forms: ['Input', 'Search', 'Select', 'MultiSelect', 'DateRange', 'Upload', 'TagEditor'],
  tables: ['Table', 'DataTable'],
  cards: ['Card', 'WalletCard', 'InvestigationCard', 'EvidenceCard'],
  graph: ['ReactFlow', 'Minimap', 'Controls', 'Background'],
  timeline: ['ActivityTimeline'],
  dashboards: ['CompliancePage', 'MetricsGrid'],
} as const

export const BREAKPOINTS = {
  laptop: 1280,
  desktop: 1920,
  wide: 2560,
  ultraWide: 3440,
} as const

export function designSystemManifest() {
  return {
    rfc: 'RFC-0008',
    schema_version: '8.0.0',
    title: 'Enterprise Design System v2.0',
    principles: DESIGN_PRINCIPLES.map((p) => ({
      id: p,
      label_ru: DESIGN_PRINCIPLES_RU[p],
    })),
    themes: [...THEMES],
    spacing_px: [...SPACING_SCALE],
    typography: [...TYPOGRAPHY_SCALE],
    semantic_colors: [...SEMANTIC_COLORS],
    risk_colors: [...RISK_COLORS],
    graph_entity_colors: [...GRAPH_ENTITY_COLORS],
    components: REQUIRED_COMPONENTS,
    breakpoints: BREAKPOINTS,
    token_css: 'src/design-system/tokens.css',
    governance: {
      requires: ['description', 'api', 'variants', 'states', 'a11y', 'examples', 'tests'],
    },
  }
}
