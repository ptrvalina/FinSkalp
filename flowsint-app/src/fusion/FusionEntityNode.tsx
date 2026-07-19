import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import {
  EntityIcon,
  resolveEntityIconKind,
  entityGraphColorVar,
} from '@/design-system/entity-icons'
import { cn } from '@/lib/utils'

type FusionEntityNodeData = {
  label?: string
  kind?: string
  cluster?: string | null
  pinned?: boolean
}

function nodeShapeClass(kind: string): string {
  const k = kind.toLowerCase()
  if (/exchange|mixer|contract|smart|bank|cex|dex/.test(k)) {
    return 'fusion-entity-node--rect'
  }
  if (/unknown|unspecified/.test(k)) {
    return 'fusion-entity-node--unknown'
  }
  return 'fusion-entity-node--circle'
}

export const FusionEntityNode = memo(function FusionEntityNode({
  data,
  selected,
}: NodeProps) {
  const nodeData = data as FusionEntityNodeData
  const rawKind = String(nodeData.kind ?? 'unknown')
  const iconKind = resolveEntityIconKind(rawKind)
  const title = String(nodeData.label ?? '').split('\n')[0] ?? nodeData.kind ?? '—'
  const accent = entityGraphColorVar(iconKind)
  const shape = nodeShapeClass(rawKind)

  return (
    <div
      className={cn(
        'fusion-entity-node',
        shape,
        selected && 'fusion-entity-node--selected',
        nodeData.pinned && 'fusion-entity-node--pinned'
      )}
      style={
        {
          '--fusion-node-accent': accent,
        } as React.CSSProperties
      }
    >
      <Handle type="target" position={Position.Left} className="fusion-entity-node__handle" />
      <div className="fusion-entity-node__glyph" style={{ color: accent }}>
        <EntityIcon kind={iconKind} size={16} />
      </div>
      <div className="fusion-entity-node__body min-w-0">
        <div className="fusion-entity-node__title truncate">{title}</div>
        <div className="fusion-entity-node__meta fusion-mono truncate">
          {nodeData.kind}
          {nodeData.cluster ? ` · ${nodeData.cluster}` : ''}
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="fusion-entity-node__handle" />
    </div>
  )
})
