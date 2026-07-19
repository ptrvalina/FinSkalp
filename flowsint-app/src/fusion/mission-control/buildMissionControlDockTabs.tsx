import { cn } from '@/lib/utils'

import { FusionReportsPanel } from '@/fusion/panels/reports-panel'

import { evidenceRowDragProps } from '@/fusion/fusion-evidence-drag'

import type { FusionDockTab } from '@/fusion/FusionDock'

import { fusionCopy } from '@/fusion/fusion-copy'

import type { MissionControlWorkspace } from './useMissionControlWorkspace'

type BuildParams = Pick<
  MissionControlWorkspace,
  | 'timelineEvents'
  | 'evidenceItems'
  | 'selectedEvidenceId'
  | 'handleEvidenceClick'
  | 'workspaceQuery'
  | 'graphQuery'
  | 'previewCaseRef'
  | 'previewCaseId'
  | 'fusion'
  | 'queueData'
>

export function buildMissionControlDockTabs({
  timelineEvents,
  evidenceItems,
  selectedEvidenceId,
  handleEvidenceClick,
  workspaceQuery,
  graphQuery,
  previewCaseRef,
  previewCaseId,
  fusion,
  queueData,
}: BuildParams): FusionDockTab[] {
  return [
    {
      id: 'timeline',
      label: fusionCopy.dock.timeline,
      content: (
        <ul className="divide-y divide-[var(--fusion-border)]">
          {timelineEvents.length === 0 ? (
            <li className="fusion-text-micro p-4 text-center">
              {fusionCopy.dock.awaitingTimelineEvents}
            </li>
          ) : (
            timelineEvents.map((ev) => (
              <li key={ev.id} className="px-3 py-2 fusion-text-data">
                <span className="fusion-text-micro fusion-mono">
                  {new Date(ev.occurred_at).toLocaleTimeString('ru-RU')}
                </span>
                <p className="mt-1 fusion-truncate">{ev.actor}</p>
              </li>
            ))
          )}
        </ul>
      ),
    },
    {
      id: 'evidence',
      label: fusionCopy.dock.evidence,
      content: (
        <ul className="divide-y divide-[var(--fusion-border)]">
          {evidenceItems.length === 0 ? (
            <li className="fusion-text-micro p-4 text-center">{fusionCopy.dock.noEvidence}</li>
          ) : (
            evidenceItems.map((item) => (
              <li
                key={item.id}
                {...evidenceRowDragProps(item.content_hash)}
                className={cn(
                  'fusion-evidence-row px-3 py-2 fusion-text-data',
                  selectedEvidenceId === item.id && 'fusion-evidence-row--active'
                )}
                role="button"
                tabIndex={0}
                onClick={() => handleEvidenceClick(item.id, item.content_hash)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    handleEvidenceClick(item.id, item.content_hash)
                  }
                }}
              >
                <span className="fusion-text-micro">{item.source_type}</span>
                <p className="fusion-truncate">{item.content_hash}</p>
              </li>
            ))
          )}
        </ul>
      ),
    },
    {
      id: 'blockchain',
      label: fusionCopy.dock.blockchain,
      content: (
        <div className="p-3 space-y-2 fusion-text-data">
          <p className="fusion-text-micro fusion-tone-chain">{fusionCopy.dock.supportedChains}</p>
          {(workspaceQuery.data?.intelligence?.supported_chains ?? []).length ? (
            (workspaceQuery.data?.intelligence?.supported_chains ?? []).map((chain) => (
              <span
                key={chain}
                className="mr-2 inline-block rounded border border-[var(--fusion-border)] px-2 py-0.5 fusion-text-micro"
              >
                {chain}
              </span>
            ))
          ) : (
            <p>—</p>
          )}
          <p className="fusion-text-micro pt-2 fusion-tone-chain">{fusionCopy.dock.graphEdges}</p>
          <p className="fusion-mono">{graphQuery.data?.edges?.length ?? '—'}</p>
        </div>
      ),
    },
    {
      id: 'reports',
      label: fusionCopy.dock.reports,
      content: previewCaseRef ? (
        <div className="p-2 [&_.enterprise-panel]:border-0">
          <FusionReportsPanel
            caseRef={previewCaseRef}
            caseId={previewCaseId}
            evidenceCount={workspaceQuery.data?.counts?.evidence}
            fusionResult={fusion ?? null}
          />
        </div>
      ) : (
        <p className="fusion-text-micro p-4 text-center">{fusionCopy.reports.selectCase}</p>
      ),
    },
    {
      id: 'tasks',
      label: fusionCopy.dock.tasks,
      content: (
        <ul className="divide-y divide-[var(--fusion-border)]">
          {queueData.length === 0 ? (
            <li className="fusion-text-micro p-4 text-center">{fusionCopy.queue.emptyDock}</li>
          ) : (
            queueData.slice(0, 12).map((row) => (
              <li key={row.case_id} className="px-3 py-2 fusion-text-data">
                <div className="flex items-center justify-between gap-2">
                  <span className="fusion-mono fusion-tone-ops">{row.case_ref ?? '—'}</span>
                  <span className="fusion-text-micro">
                    {row.sla_breached ? fusionCopy.queue.slaBreach : row.workflow_status ?? '—'}
                  </span>
                </div>
                <p className="fusion-text-micro mt-1 fusion-truncate">{row.title_ru ?? row.assignee_name}</p>
              </li>
            ))
          )}
        </ul>
      ),
    },
  ]
}
