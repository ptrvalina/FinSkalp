import { useEffect, useRef, type RefObject } from 'react'
import type Graph from 'graphology'
import type Sigma from 'sigma'

import { moneyFlowVisual } from './fusion-money-flow-types'

type Props = {
  sigmaRef: RefObject<Sigma | null>
  graphRef: RefObject<Graph | null>
  enabled: boolean
}

const MAX_EDGES = 1200

export function FusionGpuMoneyFlowOverlay({ sigmaRef, graphRef, enabled }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!enabled) return

    let raf = 0
    let t = 0

    const tick = () => {
      const sigma = sigmaRef.current
      const gol = graphRef.current
      const canvas = canvasRef.current
      const host = canvas?.parentElement

      if (!sigma || !gol || !canvas || !host) {
        raf = requestAnimationFrame(tick)
        return
      }

      const w = host.clientWidth
      const h = host.clientHeight
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w
        canvas.height = h
      }

      const ctx = canvas.getContext('2d')
      if (!ctx) {
        raf = requestAnimationFrame(tick)
        return
      }

      ctx.clearRect(0, 0, w, h)
      t += 0.016

      let drawn = 0
      gol.forEachEdge((_edge, attrs, source, target) => {
        if (drawn >= MAX_EDGES) return
        if (attrs.hidden) return
        drawn += 1

        const relType = String(attrs.label ?? attrs.rel_type ?? '')
        const visual = moneyFlowVisual(relType)
        const canvasColor =
          (visual as { canvasColor?: string }).canvasColor ?? visual.color

        const sx = gol.getNodeAttribute(source, 'x') as number
        const sy = gol.getNodeAttribute(source, 'y') as number
        const tx = gol.getNodeAttribute(target, 'x') as number
        const ty = gol.getNodeAttribute(target, 'y') as number
        const strength = Number(attrs.strength ?? 0.5)

        const sp = sigma.graphToViewport({ x: sx, y: sy })
        const tp = sigma.graphToViewport({ x: tx, y: ty })

        const speed = visual.speed + strength * 0.15
        const progress = (t * speed + drawn * 0.07) % 1
        const px = sp.x + (tp.x - sp.x) * progress
        const py = sp.y + (tp.y - sp.y) * progress

        ctx.beginPath()
        ctx.arc(px, py, visual.particleSize + strength, 0, Math.PI * 2)
        ctx.fillStyle = canvasColor
        ctx.globalAlpha = visual.type === 'sanction' ? 0.95 : 0.82
        ctx.fill()

        if (visual.dash?.length && drawn % 4 === 0) {
          ctx.setLineDash(visual.dash)
          ctx.strokeStyle = canvasColor
          ctx.globalAlpha = 0.25
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(sp.x, sp.y)
          ctx.lineTo(tp.x, tp.y)
          ctx.stroke()
          ctx.setLineDash([])
        }
      })

      raf = requestAnimationFrame(tick)
    }

    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [enabled, sigmaRef, graphRef])

  if (!enabled) return null

  return (
    <canvas
      ref={canvasRef}
      className="fusion-gpu-money-flow"
      aria-hidden
    />
  )
}
