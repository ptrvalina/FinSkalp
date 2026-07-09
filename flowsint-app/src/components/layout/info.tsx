import { memo } from 'react'
import { HelpCircle } from 'lucide-react'
import { Dialog, DialogContent, DialogTrigger } from '../ui/dialog'
import { Button } from '../ui/button'

const InfoDialog = () => {
  return (
    <>
      <Dialog>
        <DialogTrigger asChild>
          <div>
            <Button variant="ghost" size="sm" className="h-6 gap-1 text-xs">
              <HelpCircle className="h-3 w-3 opacity-60" />
            </Button>
          </div>
        </DialogTrigger>
        <DialogContent className="sm:max-w-2xl">
          <div className="p-2">
            <div className="p-2 text-sm space-y-4 overflow-y-auto max-h-[80vh]">
              <h2 className="text-base font-semibold flex items-center gap-2">О FinSkalp</h2>
              <p>
                <strong>FinSkalp</strong> — платформа <strong>крипто-комплаенса и расследований</strong>{' '}
                для регуляторов и аналитиков: скрининг, граф знаний, OSINT и blockchain intelligence.
              </p>

              <p>
                Связывает <strong>фиатные алерты</strong> с <strong>on-chain трассировкой</strong>,
                кластеризацией адресов и вероятностными отчётами для сужения серой зоны.
              </p>

              <h3 className="font-semibold">Возможности</h3>
              <ul className="list-disc list-inside space-y-1">
                <li>
                  <strong>Compliance</strong> — кейсы, workflow, fusion-анализ, SLA
                </li>
                <li>
                  <strong>Граф расследований</strong> — сущности, связи, enrichers, визуализация
                </li>
                <li>
                  <strong>Blockchain Intelligence</strong> — мультичейн, индекс блоков, риск-скоринг
                </li>
                <li>
                  <strong>Analyst Workspace</strong> — единое рабочее место и command palette
                </li>
              </ul>

              <p>
                FinSkalp предназначен для <strong>законного</strong> использования в рамках
                регуляторных и аналитических задач.
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

export default memo(InfoDialog)
