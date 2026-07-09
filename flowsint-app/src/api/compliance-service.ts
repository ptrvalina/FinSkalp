import { fetchWithAuth } from './api'

const COMPLIANCE_API =
  import.meta.env.VITE_COMPLIANCE_API?.replace(/\/$/, '') ||
  import.meta.env.VITE_API_URL?.replace(/\/$/, '') ||
  ''

async function complianceFetch(endpoint: string, options: RequestInit = {}): Promise<any> {
  const isDemoStand = Boolean(import.meta.env.VITE_COMPLIANCE_API)
  const url = `${COMPLIANCE_API}${endpoint}`

  if (isDemoStand) {
    const headers: HeadersInit = { 'Content-Type': 'application/json', ...options.headers }
    const response = await fetch(url, { ...options, headers })
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `Ошибка ${response.status}`)
    }
    if (response.status === 204) return null
    return response.json()
  }
  return fetchWithAuth(endpoint, options)
}

export type ComplianceCaseListItem = {
  id: string
  case_ref: string
  status: string
  investigation_id?: string | null
  workflow_status: string
  assignee_id?: string | null
  priority?: string
  due_at?: string | null
  sla_breached?: boolean
  created_at?: string
  updated_at?: string
}

export type WorkflowStats = {
  pipeline: Record<string, number>
  total: number
  sla_breached: number
}

export type ComplianceCase = {
  id: string
  case_ref: string
  status: string
  investigation_id?: string | null
  fusion_result?: Record<string, unknown> | null
}

export type EvidenceGraph = {
  nodes: Array<{
    id: string
    kind: string
    label: string
    region?: string | null
    confidence?: number
  }>
  edges: Array<{
    id: string
    source: string
    target: string
    rel_type: string
    strength?: number
  }>
}

export const complianceService = {
  createCase(caseRef: string, investigationId?: string) {
    return complianceFetch('/api/compliance/cases', {
      method: 'POST',
      body: JSON.stringify({
        case_ref: caseRef,
        investigation_id: investigationId ?? null
      })
    }) as Promise<ComplianceCase>
  },

  async findCaseByInvestigationId(investigationId: string) {
    const cases = await this.listCases()
    return cases.find((c) => c.investigation_id === investigationId) ?? null
  },

  getCase(caseId: string) {
    return complianceFetch(`/api/compliance/cases/${caseId}`) as Promise<ComplianceCase>
  },

  fuseCase(caseId: string, scenarioId?: string) {
    return complianceFetch(`/api/compliance/cases/${caseId}/fuse`, {
      method: 'POST',
      body: JSON.stringify({
        licensed_events: [],
        control_purchases: [],
        scenario_id: scenarioId ?? null
      })
    })
  },

  fuseCaseStream(caseId: string, scenarioId?: string) {
    const base = COMPLIANCE_API || ''
    const token = localStorage.getItem('auth-token')
    const headers: HeadersInit = { 'Content-Type': 'application/json' }
    if (token && !import.meta.env.VITE_COMPLIANCE_API) {
      headers['Authorization'] = `Bearer ${token}`
    }
    return fetch(`${base}/api/compliance/cases/${caseId}/fuse/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        licensed_events: [],
        control_purchases: [],
        scenario_id: scenarioId ?? 'p2p_rub_offshore'
      })
    })
  },

  fuseCaseAsync(caseId: string) {
    return complianceFetch(`/api/compliance/cases/${caseId}/fuse/async`, {
      method: 'POST',
      body: JSON.stringify({ licensed_events: [], control_purchases: [] })
    }) as Promise<{ run_id: string; task_id: string; status: string }>
  },

  getGraph(caseId: string) {
    return complianceFetch(`/api/compliance/cases/${caseId}/graph`) as Promise<EvidenceGraph>
  },

  screenWallet(address: string, chain?: string) {
    return complianceFetch('/api/compliance/wallets/screen', {
      method: 'POST',
      body: JSON.stringify({ address, chain, limit: 50 })
    })
  },

  seedDemo(scenarioId: string) {
    return complianceFetch(`/api/compliance/demo/seed/${scenarioId}`, { method: 'POST' })
  },

  reportPdfUrl(caseId: string) {
    return `${COMPLIANCE_API}/api/compliance/cases/${caseId}/report.pdf`
  },

  reportXlsxUrl(caseId: string) {
    return `${COMPLIANCE_API}/api/compliance/cases/${caseId}/report.xlsx`
  },

  demoHealth() {
    return complianceFetch('/api/compliance/health')
  },

  listCases(workflowStatus?: string) {
    const q = workflowStatus ? `?workflow_status=${encodeURIComponent(workflowStatus)}` : ''
    return complianceFetch(`/api/compliance/cases${q}`) as Promise<ComplianceCaseListItem[]>
  },

  getWorkflowStats() {
    return complianceFetch('/api/compliance/cases/workflow/stats') as Promise<WorkflowStats>
  },

  transitionCase(caseId: string, workflowStatus: string) {
    return complianceFetch(`/api/compliance/cases/${caseId}`, {
      method: 'PATCH',
      body: JSON.stringify({ workflow_status: workflowStatus })
    }) as Promise<ComplianceCase>
  },

  getKnowledgeModel() {
    return complianceFetch('/api/platform/v2/knowledge-model') as Promise<{
      rfc: string
      entity_types: Array<{ value: string; label_ru: string }>
      relation_types: Array<{ value: string; label_ru: string }>
    }>
  },

  getKgEntity(entityId: string) {
    return complianceFetch(`/api/platform/v2/entities/${entityId}`) as Promise<{
      entity: Record<string, unknown>
    }>
  },

  getKgEntityNeighbors(entityId: string, direction: 'both' | 'in' | 'out' = 'both') {
    return complianceFetch(
      `/api/platform/v2/entities/${entityId}/neighbors?direction=${direction}`
    ) as Promise<{
      entity_id: string
      neighbors: Array<{
        direction: string
        relation_type: string
        confidence: number
        entity: Record<string, unknown> | null
      }>
      count: number
    }>
  },

  compareKgEntityVersions(entityId: string, versionA: number, versionB: number) {
    return complianceFetch(
      `/api/platform/v2/entities/${entityId}/compare?version_a=${versionA}&version_b=${versionB}`
    ) as Promise<Record<string, unknown>>
  },

  exportKgEvidence(caseRef?: string) {
    const q = caseRef ? `?case_ref=${encodeURIComponent(caseRef)}` : ''
    return complianceFetch(`/api/platform/v2/evidence/export${q}`) as Promise<{
      evidence_count: number
      relation_count: number
      evidence: unknown[]
      relations: unknown[]
    }>
  },

  getPipelineChain() {
    return complianceFetch('/api/platform/v2/pipeline-chain') as Promise<{
      stages: Array<{ id: string; label_ru: string }>
      rule_ru: string
    }>
  },

  getIntelligenceManifest() {
    return complianceFetch('/api/platform/v2/intelligence/manifest') as Promise<{
      rfc: string
      title: string
      engines: Array<{ engine: string; title_ru: string; maturity: string }>
      rule_ru: string
    }>
  },

  runIntelligenceAnalysis(payload: {
    address?: string
    chain?: string
    case_ref?: string
    screening?: Record<string, unknown>
    attribution?: Record<string, unknown>
    mentions?: unknown[]
    publish?: boolean
  }) {
    return complianceFetch('/api/platform/v2/intelligence/analyze', {
      method: 'POST',
      body: JSON.stringify(payload)
    }) as Promise<{
      ok: boolean
      engines_run: string[]
      aggregate_risk_score: number
      risk_level: string
      recommendations: Array<{ action_ru: string; priority: string }>
    }>
  },

  getInvestigationManifest() {
    return complianceFetch('/api/platform/v2/investigation/manifest') as Promise<{
      rfc: string
      title: string
      lifecycle_stages: Record<string, { label_ru: string }>
      workspace_panels: string[]
    }>
  },

  getInvestigationWorkspace(caseRef: string) {
    return complianceFetch(
      `/api/platform/v2/investigations/${encodeURIComponent(caseRef)}/workspace`
    ) as Promise<{
      case_ref: string
      panels: string[]
      evidence_count: number
      timeline_count: number
      workflow: Record<string, unknown>
    }>
  },

  listInvestigationEvidence(caseRef: string) {
    return complianceFetch(
      `/api/platform/v2/investigations/${encodeURIComponent(caseRef)}/evidence`
    ) as Promise<{
      count: number
      items: Array<{
        id: string
        source_type: string
        content_hash: string
        status: string
        payload: Record<string, unknown>
      }>
      delete_forbidden: boolean
    }>
  },

  getCaseTimeline(caseRef: string) {
    return complianceFetch(
      `/api/platform/v2/cases/${encodeURIComponent(caseRef)}/timeline`
    ) as Promise<{
      case_ref: string
      events: Array<{
        id: string
        event_type: string
        occurred_at: string
        actor: string
        payload: Record<string, unknown>
      }>
      count: number
    }>
  },

  getIntelligenceEngineManifest() {
    return complianceFetch('/api/platform/v2/intelligence-engine/manifest') as Promise<{
      rfc: string
      title: string
      score_metrics: string[]
      questions_ru: string[]
    }>
  },

  getConnectorsManifest() {
    return complianceFetch('/api/platform/v2/connectors/manifest') as Promise<{
      rfc: string
      total: number
      categories: string[]
      connectors: Array<{ connector_id: string; title_ru: string; status: string }>
    }>
  },

  getDesignSystemManifest() {
    return complianceFetch('/api/platform/v2/design-system/manifest') as Promise<{
      rfc: string
      title: string
      themes: string[]
      principles: Array<{ id: string; label_ru: string }>
      typography: string[]
      entity_icons: string[]
      philosophy_ru: string
    }>
  },

  getRbacManifest() {
    return complianceFetch('/api/platform/v2/rbac/manifest') as Promise<{
      rfc: string
      title: string
      planes: { compliance: string[]; investigation: string[] }
      investigation_to_compliance: Record<string, string>
      rule_ru: string
      principle_ru: string
    }>
  },

  getWorkflowManifest() {
    return complianceFetch('/api/platform/v2/workflow/manifest') as Promise<{
      rfc: string
      title: string
      philosophy: Array<{ id: string; label_ru: string }>
      investigation_lifecycle: Array<{ id: string; label_ru: string; mandatory: boolean }>
      seed_object_types: Array<{ id: string; label_ru: string }>
      principle_ru: string
      rule_ru: string
    }>
  },

  getWorkflowState(caseRef: string) {
    return complianceFetch(`/api/platform/v2/workflow/state?case_ref=${encodeURIComponent(caseRef)}`) as Promise<{
      ok: boolean
      case_ref: string
      oicd_phase: string
      lifecycle: Array<{ id: string; label_ru: string; completed: boolean; current: boolean }>
      recommendations?: unknown
    }>
  },

  getWorkflowRecommendations(caseRef: string) {
    return complianceFetch(
      `/api/platform/v2/workflow/recommendations?case_ref=${encodeURIComponent(caseRef)}`
    ) as Promise<{
      ok: boolean
      recommendations: Array<{ id: string; action_ru: string; explanation_ru: string; priority: string }>
      count: number
    }>
  },

  getBlockchainIntelligenceManifest() {
    return complianceFetch('/api/platform/v2/blockchain-intelligence/manifest') as Promise<{
      rfc: string
      title: string
      supported_networks: Array<{ id: string; label_ru: string }>
      canonical_entities: string[]
      principle_ru: string
    }>
  },

  getIcfManifest() {
    return complianceFetch('/api/platform/v2/icf/manifest') as Promise<{
      rfc: string
      schema_version: string
      title_ru: string
      pipeline: string[]
      collector_count: number
      principle_ru: string
    }>
  },

  getCrifManifest() {
    return complianceFetch('/api/platform/v2/crif/manifest') as Promise<{
      rfc: string
      schema_version: string
      title_ru: string
      pipeline: string[]
      connector_count: number
      principle_ru: string
      canonical_entity_types: string[]
    }>
  },

  runCrifCheck(payload: {
    connectorId: string
    query?: Record<string, unknown>
    caseRef?: string
    organizationKey?: string
    publish?: boolean
  }) {
    return complianceFetch('/api/platform/v2/crif/check', {
      method: 'POST',
      body: JSON.stringify({
        connector_id: payload.connectorId,
        query: payload.query,
        case_ref: payload.caseRef,
        organization_key: payload.organizationKey,
        publish: payload.publish ?? true
      })
    }) as Promise<{
      ok: boolean
      connector_id: string
      stages: string[]
      compliance_check_count: number
      evidence_count: number
    }>
  },

  screenCrifSanctions(name: string) {
    return complianceFetch('/api/platform/v2/crif/sanctions/screen', {
      method: 'POST',
      body: JSON.stringify({ name })
    }) as Promise<{
      ok: boolean
      query: string
      match_count: number
      requires_analyst: boolean
      matches: Array<{ match_type: string; confidence: number; requires_analyst_confirmation: boolean }>
    }>
  },

  getCrifRules() {
    return complianceFetch('/api/platform/v2/crif/rules') as Promise<{
      ok: boolean
      rules: Array<{ rule_id: string; version: string; description_ru: string }>
    }>
  },

  evaluateCrifRules(context: Record<string, unknown>) {
    return complianceFetch('/api/platform/v2/crif/rules/evaluate', {
      method: 'POST',
      body: JSON.stringify({ context })
    }) as Promise<{
      ok: boolean
      event_count: number
      events: Array<{ rule_id: string; event_type: string; severity: string; message_ru: string }>
    }>
  },

  getCrifMetrics() {
    return complianceFetch('/api/platform/v2/crif/metrics') as Promise<{
      ok: boolean
      total_connectors: number
      connectors: Array<{ connector_id: string; request_count: number; checks_run: number }>
    }>
  },

  getCrifHistory(entityKey: string) {
    return complianceFetch(`/api/platform/v2/crif/history/${encodeURIComponent(entityKey)}`) as Promise<{
      ok: boolean
      entity_key: string
      count: number
      timeline: Array<{ event_type: string; field: string; new_value: unknown; source: string }>
    }>
  },

  analyzeBlockchainAddress(payload: { address: string; chain: string; caseRef?: string }) {
    return complianceFetch('/api/platform/v2/blockchain-intelligence/analyze', {
      method: 'POST',
      body: JSON.stringify({
        address: payload.address,
        chain: payload.chain,
        case_ref: payload.caseRef,
        publish: true
      })
    }) as Promise<{
      ok: boolean
      profile: Record<string, unknown>
      flow_graph: { nodes: unknown[]; edges: unknown[] }
      explain: Record<string, unknown>
    }>
  },

  getAnalystWorkspaceManifest() {
    return complianceFetch('/api/platform/v2/analyst-workspace/manifest') as Promise<{
      rfc: string
      title: string
      principle_ru: string
      workspace_tabs: string[]
      workspace_tabs_ru: Record<string, string>
      navigation_modules: string[]
      command_palette: Array<{ id: string; label_ru: string; shortcut?: string; level?: string }>
      performance_slas: Record<string, string>
    }>
  },

  getAnalystWorkspaceState(payload: { caseRef?: string; investigationId?: string }) {
    const params = new URLSearchParams()
    if (payload.caseRef) params.set('case_ref', payload.caseRef)
    if (payload.investigationId) params.set('investigation_id', payload.investigationId)
    const q = params.toString() ? `?${params.toString()}` : ''
    return complianceFetch(`/api/platform/v2/analyst-workspace/state${q}`) as Promise<{
      ok: boolean
      case_ref: string | null
      investigation_id: string | null
      active_tab?: string
      latency_ms?: number
      tabs: string[]
      workspace: {
        case_ref: string
        panels: string[]
        evidence_count: number
        timeline_count: number
        workflow: Record<string, unknown>
      }
      evidence: {
        count: number
        items: Array<{
          id: string
          source_type: string
          content_hash: string
          status: string
          payload: Record<string, unknown>
        }>
      }
      timeline: {
        count: number
        events: Array<{
          id: string
          event_type: string
          occurred_at: string
          actor: string
          payload: Record<string, unknown>
        }>
      }
      intelligence: {
        engines_count: number
        osint_categories: string[]
        supported_chains: string[]
        rule_ru?: string
      }
      collaboration?: {
        comments: Array<{
          id: string
          text: string
          author: string
          created_at: string
        }>
        activity: Array<{
          id: string
          event_type: string
          occurred_at: string
          actor?: string
          payload?: Record<string, unknown>
        }>
        comments_count: number
      }
      notifications?: Array<{
        id: string
        type: string
        label_ru: string
        occurred_at?: string
        actor?: string
        read: boolean
        payload?: Record<string, unknown>
      }>
      personalization?: Record<string, unknown>
      counts: {
        evidence: number
        timeline: number
        panels: number
        notifications_unread?: number
      }
    }>
  },

  searchAnalystWorkspace(payload: { query: string; caseRef?: string }) {
    const params = new URLSearchParams({ q: payload.query })
    if (payload.caseRef) params.set('case_ref', payload.caseRef)
    return complianceFetch(`/api/platform/v2/analyst-workspace/search?${params.toString()}`) as Promise<{
      ok: boolean
      query: string
      latency_ms?: number
      results: Array<{
        id: string
        kind: 'case' | 'entity' | 'evidence'
        display_name?: string
        canonical_key?: string
        entity_type?: string
        case_ref?: string
        source_type?: string
        content_hash?: string
      }>
      counts: { cases: number; entities: number; evidence: number; total: number }
    }>
  },

  postAnalystWorkspaceComment(payload: { caseRef: string; text: string; author?: string }) {
    return complianceFetch('/api/platform/v2/analyst-workspace/collaboration/comment', {
      method: 'POST',
      body: JSON.stringify({
        case_ref: payload.caseRef,
        text: payload.text,
        author: payload.author ?? 'analyst',
      }),
    }) as Promise<{ ok: boolean; comment: { id: string; text: string; author: string; created_at: string } }>
  },

  getAnalystWorkspaceCollaboration(caseRef: string) {
    return complianceFetch(
      `/api/platform/v2/analyst-workspace/collaboration/activity?case_ref=${encodeURIComponent(caseRef)}`
    ) as Promise<{
      ok: boolean
      comments: Array<{ id: string; text: string; author: string; created_at: string }>
      activity: Array<{
        id: string
        event_type: string
        occurred_at: string
        actor?: string
        payload?: Record<string, unknown>
      }>
    }>
  },

  getAnalystWorkspacePersonalization() {
    return complianceFetch('/api/platform/v2/analyst-workspace/personalization') as Promise<{
      ok: boolean
      preferences: Record<string, unknown>
    }>
  },

  saveAnalystWorkspacePersonalization(preferences: Record<string, unknown>) {
    return complianceFetch('/api/platform/v2/analyst-workspace/personalization', {
      method: 'PUT',
      body: JSON.stringify({ preferences }),
    }) as Promise<{ ok: boolean; preferences: Record<string, unknown> }>
  },

  runIntelligenceEngine(payload: {
    address?: string
    chain?: string
    case_ref?: string
    screening?: Record<string, unknown>
    attribution?: Record<string, unknown>
    mentions?: unknown[]
    publish?: boolean
  }) {
    return complianceFetch('/api/platform/v2/intelligence-engine/run', {
      method: 'POST',
      body: JSON.stringify(payload)
    }) as Promise<{
      ok: boolean
      scores: Record<string, number>
      weakest_score: { metric: string; value: number }
      hypotheses: Array<{ statement_ru: string; confidence: number }>
      recommendations: Array<{ action_ru: string; priority: string }>
      questions_answered: Record<string, string>
    }>
  },

  createGraphSnapshot() {
    return complianceFetch('/api/platform/v2/graph/snapshot', { method: 'POST' }) as Promise<
      Record<string, unknown>
    >
  }
}
