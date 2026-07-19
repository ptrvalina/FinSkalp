/** Unified intelligence stream bus — SSE, MIO, graph diff, evidence, risk (U3) */

export type IntelligenceStreamKind =
  | 'sse'
  | 'mio'
  | 'graph_diff'
  | 'evidence'
  | 'risk'
  | 'timeline'

export type IntelligenceStreamAction =
  | { type: 'focus_node'; nodeId: string }
  | { type: 'open_dock'; tab: string }
  | { type: 'replay_index'; index: number }
  | { type: 'fly_to'; nodeId: string }

export type IntelligenceStreamItem = {
  id: string
  kind: IntelligenceStreamKind
  ts: number
  title: string
  detail?: string
  severity?: 'critical' | 'warning' | 'info' | 'clear'
  action?: IntelligenceStreamAction
  nodeId?: string
}

type Listener = (items: IntelligenceStreamItem[]) => void

const MAX_ITEMS = 80
let items: IntelligenceStreamItem[] = []
const listeners = new Set<Listener>()

function emit() {
  const snapshot = [...items]
  listeners.forEach((fn) => fn(snapshot))
}

export function getIntelligenceStreamItems(): IntelligenceStreamItem[] {
  return [...items]
}

export function subscribeIntelligenceStream(fn: Listener): () => void {
  listeners.add(fn)
  fn([...items])
  return () => listeners.delete(fn)
}

export function pushIntelligenceItem(item: IntelligenceStreamItem): void {
  if (items.some((i) => i.id === item.id)) return
  items = [item, ...items].slice(0, MAX_ITEMS)
  emit()
}

export function pushIntelligenceItems(batch: IntelligenceStreamItem[]): void {
  if (!batch.length) return
  const existing = new Set(items.map((i) => i.id))
  const fresh = batch.filter((i) => !existing.has(i.id))
  if (!fresh.length) return
  items = [...fresh, ...items].slice(0, MAX_ITEMS)
  emit()
}

export function clearIntelligenceStream(): void {
  items = []
  emit()
}
