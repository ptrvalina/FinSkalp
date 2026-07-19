import { useMemo } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { ReportCaseBundle } from './report-types'
import { deriveReportRisk, reportEdges } from './report-intel'

type FlowRow = { lane: string; value: number; fill: string }

const FLOW_COLORS = ['#3b82f6', '#06b6d4', '#8b5cf6', '#f59e0b', '#ef4444', '#10b981']

function buildFlowRows(bundle: ReportCaseBundle): FlowRow[] {
  const bridges = (bundle.fusion?.bridges as Array<Record<string, unknown>> | undefined) ?? []
  if (bridges.length) {
    return bridges.slice(0, 8).map((b, i) => ({
      lane: String(b.type ?? b.id ?? b.from ?? `Bridge ${i + 1}`).slice(0, 28),
      value: Number(b.amount ?? b.volume ?? b.weight ?? 1) || 1,
      fill: FLOW_COLORS[i % FLOW_COLORS.length],
    }))
  }

  const edges = reportEdges(bundle)
  const counts = new Map<string, number>()
  for (const e of edges) {
    const key = e.rel_type ?? 'link'
    counts.set(key, (counts.get(key) ?? 0) + (Number(e.strength) || 1))
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([lane, value], i) => ({
      lane: lane.slice(0, 28),
      value: Math.round(value * 10) / 10,
      fill: FLOW_COLORS[i % FLOW_COLORS.length],
    }))
}

export function ReportMoneyFlowChart({
  bundle,
  compact = false,
}: {
  bundle: ReportCaseBundle
  compact?: boolean
}) {
  const rows = useMemo(() => buildFlowRows(bundle), [bundle])

  if (!rows.length) {
    return (
      <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
        No flow data — run Fusion or collect graph edges.
      </p>
    )
  }

  return (
    <div
      className={compact ? 'fusion-report-chart fusion-report-chart--compact' : 'fusion-report-chart'}
      data-testid="fusion-report-money-flow-chart"
    >
      <ResponsiveContainer width="100%" height={compact ? 88 : 220}>
        <BarChart data={rows} layout="vertical" margin={{ left: 4, right: 12, top: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
          <XAxis type="number" hide={compact} tick={{ fill: 'var(--fusion-text-tertiary)', fontSize: 10 }} />
          <YAxis
            type="category"
            dataKey="lane"
            width={compact ? 72 : 120}
            tick={{ fill: 'var(--fusion-text-tertiary)', fontSize: 10 }}
          />
          {!compact ? (
            <Tooltip
              contentStyle={{
                background: 'var(--fusion-bg-panel)',
                border: '1px solid var(--fusion-border)',
                fontSize: 11,
              }}
            />
          ) : null}
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {rows.map((row) => (
              <Cell key={row.lane} fill={row.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ReportRiskHeatmap({
  bundle,
  compact = false,
}: {
  bundle: ReportCaseBundle
  compact?: boolean
}) {
  const points = bundle.riskHistory.points
  const derived = useMemo(() => deriveReportRisk(bundle), [bundle])
  const chartData = useMemo(() => {
    if (points.length) {
      return points.slice(-24).map((p) => ({
        ts: new Date(p.ts).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }),
        score: p.score,
      }))
    }
    const score = Number(bundle.fusion?.illegal_flow_score)
    if (Number.isFinite(score) && score > 0) {
      return [{ ts: 'now', score: score <= 1 ? score * 100 : score }]
    }
    if (derived.score > 0) {
      return [{ ts: 'derived', score: derived.score }]
    }
    return []
  }, [points, bundle.fusion?.illegal_flow_score, derived.score])

  if (!chartData.length) {
    return (
      <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
        Нет риск-метрик — соберите граф или выполните KYT.
      </p>
    )
  }

  return (
    <div
      className={compact ? 'fusion-report-chart fusion-report-chart--compact' : 'fusion-report-chart'}
      data-testid="fusion-report-risk-heatmap"
    >
      <ResponsiveContainer width="100%" height={compact ? 72 : 200}>
        <AreaChart data={chartData} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
          <defs>
            <linearGradient id="riskHeat" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef4444" stopOpacity={0.55} />
              <stop offset="100%" stopColor="#ef4444" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="ts" hide={compact} tick={{ fill: 'var(--fusion-text-tertiary)', fontSize: 10 }} />
          <YAxis hide={compact} tick={{ fill: 'var(--fusion-text-tertiary)', fontSize: 10 }} />
          {!compact ? (
            <Tooltip
              contentStyle={{
                background: 'var(--fusion-bg-panel)',
                border: '1px solid var(--fusion-border)',
                fontSize: 11,
              }}
            />
          ) : null}
          <Area type="monotone" dataKey="score" stroke="#ef4444" fill="url(#riskHeat)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
