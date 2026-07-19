import { describe, expect, it } from 'vitest'

import {
  applyFastLayout,
  buildSyntheticGraph,
  createViewportReducer,
  isNodeInViewport,
  measureGraphBuildMs,
} from '../fusion-gpu-graph-engine'

describe('fusion-gpu-graph-engine', () => {
  it('buildSyntheticGraph produces correct node count', () => {
    const g = buildSyntheticGraph(100, 4)
    expect(g.order).toBe(100)
    expect(g.size).toBeGreaterThan(0)
  })

  it('buildSyntheticGraph respects avgDegree target', () => {
    const g = buildSyntheticGraph(50, 6)
    expect(g.order).toBe(50)
    expect(g.size).toBeGreaterThanOrEqual(40)
    expect(g.size).toBeLessThanOrEqual(200)
  })

  it('applyFastLayout sets x/y on all nodes (grid)', () => {
    const g = buildSyntheticGraph(64, 2)
    applyFastLayout(g, 'grid')
    g.forEachNode((node) => {
      const x = g.getNodeAttribute(node, 'x') as number
      const y = g.getNodeAttribute(node, 'y') as number
      expect(Number.isFinite(x)).toBe(true)
      expect(Number.isFinite(y)).toBe(true)
    })
  })

  it('applyFastLayout sets x/y on all nodes (circle)', () => {
    const g = buildSyntheticGraph(32, 2)
    applyFastLayout(g, 'circle')
    g.forEachNode((node) => {
      const x = g.getNodeAttribute(node, 'x') as number
      const y = g.getNodeAttribute(node, 'y') as number
      expect(Number.isFinite(x)).toBe(true)
      expect(Number.isFinite(y)).toBe(true)
    })
  })

  it('viewport reducer hides nodes outside viewport', () => {
    const g = buildSyntheticGraph(100, 2)
    applyFastLayout(g, 'grid')

    const camera = { x: 40, y: 40, ratio: 0.25 }
    const { nodeReducer } = createViewportReducer(g, camera, 200, 200, 0)

    let hidden = 0
    let visible = 0
    g.forEachNode((node) => {
      const result = nodeReducer(node, g.getNodeAttributes(node))
      if (result.hidden) hidden++
      else visible++
    })

    expect(hidden).toBeGreaterThan(0)
    expect(visible).toBeGreaterThan(0)
    expect(hidden + visible).toBe(g.order)
  })

  it('isNodeInViewport matches reducer visibility at center', () => {
    const g = buildSyntheticGraph(10, 2)
    applyFastLayout(g, 'circle')
    const camera = { x: 0, y: 0, ratio: 1 }
    const { nodeReducer } = createViewportReducer(g, camera, 800, 600)

    g.forEachNode((node) => {
      const x = g.getNodeAttribute(node, 'x') as number
      const y = g.getNodeAttribute(node, 'y') as number
      const inView = isNodeInViewport(x, y, camera, 800, 600)
      const reduced = nodeReducer(node, g.getNodeAttributes(node))
      expect(Boolean(reduced.hidden)).toBe(!inView)
    })
  })
})

describe('fusion-gpu-graph-engine perf gates', () => {
  it('builds 5k nodes in < 500ms', () => {
    const ms = measureGraphBuildMs(5000)
    expect(ms).toBeLessThan(500)
  })

  it('builds 20k nodes in < 2000ms', () => {
    const ms = measureGraphBuildMs(20_000)
    expect(ms).toBeLessThan(2000)
  })

  it('layouts 100k nodes in < 3000ms', () => {
    const g = buildSyntheticGraph(100_000, 3)
    const start = performance.now()
    applyFastLayout(g, 'grid')
    const ms = performance.now() - start
    expect(ms).toBeLessThan(3000)
  })

  it('viewport reducer pass on 100k graph < 100ms for 1000 checks', () => {
    const g = buildSyntheticGraph(100_000, 3)
    applyFastLayout(g, 'grid')
    const camera = { x: 0, y: 0, ratio: 2 }
    const { nodeReducer } = createViewportReducer(g, camera, 800, 600)

    const start = performance.now()
    for (let i = 0; i < 1000; i++) {
      const node = `node-${i}`
      nodeReducer(node, g.getNodeAttributes(node))
    }
    const ms = performance.now() - start
    expect(ms).toBeLessThan(100)
  })
})
