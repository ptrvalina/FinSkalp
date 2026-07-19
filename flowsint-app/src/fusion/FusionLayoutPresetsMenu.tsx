import { useState } from 'react'
import {
  deleteLayoutPreset,
  loadLayoutPresets,
  saveLayoutPreset,
  applyLayoutPreset,
  setGpuGraphEnabled,
  isGpuGraphEnabled,
  type LayoutPreset,
} from './fusion-layout-presets'

type Props = {
  open: boolean
  onClose: () => void
}

export function FusionLayoutPresetsMenu({ open, onClose }: Props) {
  const [presets, setPresets] = useState<LayoutPreset[]>(() => loadLayoutPresets())
  const [name, setName] = useState('')
  const [gpu, setGpu] = useState(isGpuGraphEnabled())

  if (!open) return null

  const refresh = () => setPresets(loadLayoutPresets())

  return (
    <div
      className="fixed inset-0 z-[215] flex items-start justify-center bg-black/60 p-4 pt-[12vh]"
      role="dialog"
      aria-label="Раскладки рабочего места"
      onClick={onClose}
    >
      <div
        className="fusion-surface-panel w-full max-w-md p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="fusion-heading-panel mb-3">Рабочие раскладки</h2>

        <div className="mb-4 flex gap-2">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Имя пресета…"
            className="flex-1 border border-[var(--fusion-border)] bg-transparent px-2 py-1 fusion-text-data outline-none"
          />
          <button
            type="button"
            className="px-3 py-1 fusion-text-micro text-[var(--fusion-ops-blue)] border border-[var(--fusion-border)]"
            onClick={() => {
              if (!name.trim()) return
              saveLayoutPreset(name.trim())
              setName('')
              refresh()
            }}
          >
            Сохранить
          </button>
        </div>

        <ul className="mb-4 max-h-48 overflow-auto divide-y divide-[var(--fusion-border)]">
          {presets.length === 0 ? (
            <li className="fusion-text-micro py-3 text-center text-[var(--fusion-text-tertiary)]">
              Нет сохранённых пресетов
            </li>
          ) : (
            presets.map((p) => (
              <li key={p.id} className="flex items-center gap-2 py-2">
                <button
                  type="button"
                  className="flex-1 text-left fusion-text-data hover:text-[var(--fusion-ops-blue)]"
                  onClick={() => applyLayoutPreset(p)}
                >
                  {p.name}
                  <span className="fusion-text-micro ml-2 text-[var(--fusion-text-tertiary)]">
                    {new Date(p.savedAt).toLocaleDateString('ru-RU')}
                  </span>
                </button>
                <button
                  type="button"
                  className="fusion-text-micro text-[var(--fusion-ops-red)]"
                  onClick={() => {
                    deleteLayoutPreset(p.id)
                    refresh()
                  }}
                >
                  ×
                </button>
              </li>
            ))
          )}
        </ul>

        <label className="flex items-center gap-2 fusion-text-data cursor-pointer">
          <input
            type="checkbox"
            checked={gpu}
            onChange={(e) => {
              setGpu(e.target.checked)
              setGpuGraphEnabled(e.target.checked)
            }}
          />
          WebGL GPU Graph (100k+ nodes)
        </label>
        <p className="fusion-text-micro mt-1 text-[var(--fusion-text-tertiary)]">
          Перезагрузка страницы применит движок
        </p>

        <button
          type="button"
          className="mt-4 w-full py-2 fusion-text-micro border border-[var(--fusion-border)]"
          onClick={() => window.location.reload()}
        >
          Применить GPU / перезагрузить
        </button>
      </div>
    </div>
  )
}
