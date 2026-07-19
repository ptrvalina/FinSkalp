/** Operator-facing investigation stages — single source of truth for progress UI. */

export type InvestigationStageId =
  | 'seed'
  | 'collect'
  | 'kyt'
  | 'fusion'
  | 'reports'

export type InvestigationStageStatus = 'done' | 'current' | 'todo'

export type InvestigationStage = {
  id: InvestigationStageId
  index: number
  label: string
  status: InvestigationStageStatus
}

export type InvestigationPhaseSnapshot = {
  stages: InvestigationStage[]
  currentId: InvestigationStageId
  /** One sentence: where we are now */
  nowLabel: string
  /** Exact next operator action */
  nextActionLabel: string
  nextActionKind: 'collect' | 'kyt' | 'fuse' | 'reports' | 'wait' | 'none'
  progressPct: number
  finished: boolean
}

const STAGE_DEFS: Array<{ id: InvestigationStageId; label: string }> = [
  { id: 'seed', label: '1. Seed' },
  { id: 'collect', label: '2. Collect' },
  { id: 'kyt', label: '3. KYT' },
  { id: 'fusion', label: '4. Fusion' },
  { id: 'reports', label: '5. Отчёт' },
]

export type ResolveInvestigationPhaseInput = {
  hasSeed: boolean
  nodeCount: number
  pipelineActive: boolean
  pipelineError: boolean
  kytDone: boolean
  /** Skip KYT stage when there is no wallet to screen */
  kytApplicable: boolean
  fusionDone: boolean
  hasReports?: boolean
}

export function resolveInvestigationPhase(
  input: ResolveInvestigationPhaseInput
): InvestigationPhaseSnapshot {
  const {
    hasSeed,
    nodeCount,
    pipelineActive,
    pipelineError,
    kytDone,
    kytApplicable,
    fusionDone,
    hasReports = false,
  } = input

  const seedDone = hasSeed
  const collectDone = nodeCount > 0 && !pipelineActive
  /** Fusion already ran — do not block on missing local KYT session flag */
  const kytStageDone = !kytApplicable || kytDone || fusionDone
  const fusionStageDone = fusionDone
  const reportsDone = hasReports || (fusionDone && hasReports)

  let currentId: InvestigationStageId = 'seed'
  if (!seedDone) currentId = 'seed'
  else if (pipelineActive || pipelineError || !collectDone) currentId = 'collect'
  else if (!kytStageDone) currentId = 'kyt'
  else if (!fusionStageDone) currentId = 'fusion'
  else currentId = 'reports'

  const doneFlags: Record<InvestigationStageId, boolean> = {
    seed: seedDone && currentId !== 'seed',
    collect: collectDone && (kytStageDone || currentId === 'kyt' || currentId === 'fusion' || currentId === 'reports'),
    kyt: kytStageDone && (fusionStageDone || currentId === 'fusion' || currentId === 'reports'),
    fusion: fusionStageDone,
    reports: Boolean(hasReports),
  }

  // Mark completed stages up to (not including) current when prior gates passed
  if (seedDone) doneFlags.seed = true
  if (collectDone) doneFlags.collect = true
  if (kytStageDone && collectDone) doneFlags.kyt = true
  if (fusionStageDone) doneFlags.fusion = true
  if (hasReports) doneFlags.reports = true

  const stages: InvestigationStage[] = STAGE_DEFS.map((def, index) => {
    let status: InvestigationStageStatus = 'todo'
    if (def.id === currentId) status = 'current'
    else if (doneFlags[def.id]) status = 'done'
    return { ...def, index: index + 1, status }
  })

  const doneCount = stages.filter((s) => s.status === 'done').length
  const progressPct = Math.round((doneCount / stages.length) * 100)
  const finished = fusionStageDone && (hasReports || currentId === 'reports')

  let nowLabel = ''
  let nextActionLabel = ''
  let nextActionKind: InvestigationPhaseSnapshot['nextActionKind'] = 'none'

  switch (currentId) {
    case 'seed':
      nowLabel = 'Этап 1/5 · Нужен объект расследования (кошелёк / person)'
      nextActionLabel = 'Collect · Seed'
      nextActionKind = 'collect'
      break
    case 'collect':
      if (pipelineActive) {
        nowLabel = 'Этап 2/5 · Идёт сбор Scalpel…'
        nextActionLabel = 'Ждите завершения сбора'
        nextActionKind = 'wait'
      } else if (pipelineError) {
        nowLabel = 'Этап 2/5 · Ошибка сбора'
        nextActionLabel = 'Повторить collectors'
        nextActionKind = 'collect'
      } else {
        nowLabel = 'Этап 2/5 · Запустите collectors'
        nextActionLabel = 'Запустить collectors'
        nextActionKind = 'collect'
      }
      break
    case 'kyt':
      nowLabel = 'Этап 3/5 · Нужен KYT-скрининг кошелька'
      nextActionLabel = 'Выполнить KYT'
      nextActionKind = 'kyt'
      break
    case 'fusion':
      nowLabel = `Этап 4/5 · Граф готов (${nodeCount} узлов) — запустите Fusion`
      nextActionLabel = 'Запустить Fusion'
      nextActionKind = 'fuse'
      break
    case 'reports':
      nowLabel = finished
        ? 'Этап 5/5 · Расследование завершено — отчёты доступны'
        : 'Этап 5/5 · Fusion готов — откройте отчёты'
      nextActionLabel = 'Открыть отчёты'
      nextActionKind = 'reports'
      break
  }

  return {
    stages,
    currentId,
    nowLabel,
    nextActionLabel,
    nextActionKind,
    progressPct: finished ? 100 : Math.max(progressPct, currentId === 'reports' ? 80 : progressPct),
    finished,
  }
}
