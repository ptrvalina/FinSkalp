import type Graph from 'graphology'

/** Offload force layout to WebWorker when graph exceeds this node count. */
export const WORKER_LAYOUT_THRESHOLD = 5000

let worker: Worker | null = null

function getLayoutWorker(): Worker {
  if (!worker) {
    worker = new Worker(new URL('../workers/layout.worker.ts', import.meta.url), {
      type: 'module',
    })
  }
  return worker
}

export function terminateFusionLayoutWorker(): void {
  worker?.terminate()
  worker = null
}

export async function applyWorkerLayoutToGraphology(
  g: Graph,
  width: number,
  height: number
): Promise<void> {
  const nodeCount = g.order
  if (nodeCount < WORKER_LAYOUT_THRESHOLD) return

  const nodes = g.nodes().map((id) => ({
    id,
    x: g.getNodeAttribute(id, 'x') as number | undefined,
    y: g.getNodeAttribute(id, 'y') as number | undefined,
    nodeLabel: String(g.getNodeAttribute(id, 'label') ?? id).slice(0, 32),
  }))

  const edges = g.edges().map((edgeKey) => {
    const [source, target] = g.extremities(edgeKey)
    return { id: edgeKey, source, target }
  })

  const iterations = nodeCount > 50_000 ? 60 : nodeCount > 20_000 ? 90 : nodeCount > 10_000 ? 120 : 180

  return new Promise((resolve, reject) => {
    const w = getLayoutWorker()

    const handleMessage = (event: MessageEvent) => {
      if (event.data.type === 'complete') {
        const { nodes: layoutedNodes } = event.data.result as {
          nodes: Array<{ id: string; x?: number; y?: number }>
        }
        for (const n of layoutedNodes) {
          if (n.x != null && n.y != null) {
            g.setNodeAttribute(n.id, 'x', n.x)
            g.setNodeAttribute(n.id, 'y', n.y)
          }
        }
        w.removeEventListener('message', handleMessage)
        w.removeEventListener('error', handleError)
        resolve()
      } else if (event.data.type === 'error') {
        w.removeEventListener('message', handleMessage)
        w.removeEventListener('error', handleError)
        reject(new Error(event.data.error))
      }
    }

    const handleError = (err: ErrorEvent) => {
      w.removeEventListener('message', handleMessage)
      w.removeEventListener('error', handleError)
      reject(err)
    }

    w.addEventListener('message', handleMessage)
    w.addEventListener('error', handleError)

    w.postMessage({
      type: 'force',
      nodes,
      edges,
      options: {
        width: width || 800,
        height: height || 600,
        chargeStrength: nodeCount > 20_000 ? -40 : -80,
        linkDistance: nodeCount > 20_000 ? 4 : 8,
        linkStrength: 0.6,
        iterations,
        centerGravity: 0.18,
        collisionRadius: nodeCount > 20_000 ? 6 : 10,
      },
    })
  })
}
