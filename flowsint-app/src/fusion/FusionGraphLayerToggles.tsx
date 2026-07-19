import { cn } from '@/lib/utils'
import type { GraphLayerToggles } from './fusion-graph-layers'
import { toggleGraphLayer } from './fusion-sync-bus'

const LAYERS: Array<{ key: keyof GraphLayerToggles; label: string }> = [
  { key: 'entities', label: 'Entities' },
  { key: 'transactions', label: 'Tx' },
  { key: 'evidence', label: 'Evidence' },
  { key: 'crossCase', label: 'Cross' },
]

type Props = {
  layers: GraphLayerToggles
  className?: string
}

export function FusionGraphLayerToggles({ layers, className }: Props) {
  return (
    <div className={cn('fusion-graph-layers', className)} role="group" aria-label="Graph layers">
      {LAYERS.map(({ key, label }) => {
        const active = layers[key]
        return (
          <button
            key={key}
            type="button"
            className={cn(
              'fusion-graph-hud__chip fusion-graph-hud__chip--interactive',
              active && 'fusion-graph-hud__chip--active'
            )}
            aria-pressed={active}
            aria-label={`${label} layer ${active ? 'on' : 'off'}`}
            onClick={() => toggleGraphLayer(key)}
            title={`Toggle ${label} layer`}
          >
            <span className="fusion-graph-hud__chip-label">{label}</span>
            <span className="fusion-graph-hud__chip-value">{active ? 'ON' : 'OFF'}</span>
          </button>
        )
      })}
    </div>
  )
}
