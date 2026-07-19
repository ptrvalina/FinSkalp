type GraphNode = { id: string; kind?: string; label?: string; confidence?: number }
type GraphEdge = { id?: string; source: string; target: string; rel_type?: string }

export function graphNodesToCsv(nodes: GraphNode[]): string {
  const esc = (v: string) => `"${v.replace(/"/g, '""')}"`
  const header = 'id,kind,label,confidence'
  const rows = nodes.map((n) =>
    [n.id, n.kind ?? '', n.label ?? '', n.confidence ?? ''].map((c) => esc(String(c))).join(',')
  )
  return [header, ...rows].join('\n')
}

export function graphToGraphMl(graph: { nodes: GraphNode[]; edges: GraphEdge[] }): string {
  const esc = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  const keys = `
    <key id="kind" for="node" attr.name="kind" attr.type="string"/>
    <key id="label" for="node" attr.name="label" attr.type="string"/>
    <key id="rel_type" for="edge" attr.name="rel_type" attr.type="string"/>`

  const nodes = graph.nodes
    .map(
      (n) =>
        `<node id="${esc(n.id)}"><data key="kind">${esc(n.kind ?? '')}</data><data key="label">${esc(n.label ?? n.id)}</data></node>`
    )
    .join('\n')

  const edges = graph.edges
    .map((e, i) => {
      const id = esc(e.id ?? `e${i}`)
      const rel = e.rel_type ? `<data key="rel_type">${esc(e.rel_type)}</data>` : ''
      return `<edge id="${id}" source="${esc(e.source)}" target="${esc(e.target)}">${rel}</edge>`
    })
    .join('\n')

  return `<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
${keys}
  <graph edgedefault="directed">
${nodes}
${edges}
  </graph>
</graphml>`
}

export function downloadTextFile(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function downloadJsonFile(filename: string, data: unknown): void {
  downloadTextFile(filename, JSON.stringify(data, null, 2), 'application/json')
}
