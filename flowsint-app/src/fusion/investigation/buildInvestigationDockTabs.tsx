import { FusionWalletsPanel } from '@/fusion/panels/wallets-panel'
import { FusionReportsPanel } from '@/fusion/panels/reports-panel'

import { FusionEvidenceObject, setEvidenceDragData } from '@/fusion'
import type { FusionDockTab } from '@/fusion/FusionDock'

import { fusionCopy } from '@/fusion/fusion-copy'

import type { InvestigationWorkspace } from './useInvestigationWorkspace'

type BuildParams = Pick<
  InvestigationWorkspace,
  | 'timelineEvents'
  | 'evidenceItems'
  | 'selectedEvidenceId'
  | 'handleEvidenceClick'
  | 'resolveEvidenceNodeId'
  | 'workspaceQuery'
  | 'graphQuery'
  | 'screenMutation'
  | 'caseRef'
  | 'caseId'
  | 'fusion'
>

export function buildInvestigationDockTabs({
  timelineEvents,
  evidenceItems,
  selectedEvidenceId,
  handleEvidenceClick,
  resolveEvidenceNodeId,
  workspaceQuery,
  graphQuery,
  screenMutation,
  caseRef,
  caseId,
  fusion,
}: BuildParams): FusionDockTab[] {
  return [
    {
      id: 'transactions',
      label: fusionCopy.dock.transactions,
      content: (
        <ul className="divide-y divide-[var(--fusion-border)]">
          {timelineEvents.filter((e) => /tx|transfer|transaction/i.test(e.event_type)).length ===
          0 ? (
            <li className="fusion-text-micro p-4 text-center">
              {fusionCopy.dock.noTransactionEvents}
            </li>
          ) : (
            timelineEvents
              .filter((e) => /tx|transfer|transaction/i.test(e.event_type))
              .map((ev) => (
                <li key={ev.id} className="px-3 py-2 fusion-text-data">
                  <span className="fusion-text-micro">{ev.event_type}</span>
                  <p className="fusion-truncate">{ev.actor}</p>
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
            <li className="fusion-text-micro p-4 text-center">{fusionCopy.dock.noEvidenceItems}</li>
          ) : (
            evidenceItems.map((item) => (
              <li key={item.id} className="px-2 py-1">
                <FusionEvidenceObject
                  id={item.id}
                  sourceType={item.source_type}
                  contentHash={item.content_hash}
                  status={item.status}
                  payload={item.payload}
                  linkedEntityCount={resolveEvidenceNodeId(item.content_hash) ? 1 : 0}
                  active={selectedEvidenceId === item.id}
                  draggable
                  onDragStart={(e) => setEvidenceDragData(e, item.content_hash)}
                  onClick={() => handleEvidenceClick(item.id, item.content_hash)}
                />
              </li>
            ))
          )}
        </ul>
      ),
    },
    {
      id: 'osint',
      label: fusionCopy.dock.osint,
      content: (
        <ul className="divide-y divide-[var(--fusion-border)]">
          {evidenceItems.filter((i) => i.source_type?.toLowerCase().includes('osint')).length ===
          0 ? (
            <li className="fusion-text-micro p-4 text-center">
              {fusionCopy.dock.noOsintEvidence}
            </li>
          ) : (
            evidenceItems
              .filter((i) => i.source_type?.toLowerCase().includes('osint'))
              .map((item) => (
                <li key={item.id} className="px-3 py-2 fusion-text-data">
                  {item.content_hash}
                </li>
              ))
          )}
        </ul>
      ),
    },
    {
      id: 'wallets',
      label: fusionCopy.dock.wallets,
      content: (
        <div className="p-2 [&_.enterprise-panel]:border-0">
          <FusionWalletsPanel
            evidenceItems={evidenceItems}
            supportedChains={workspaceQuery.data?.intelligence?.supported_chains ?? []}
            onScreenWallet={(address, chain) => screenMutation.mutate({ address, chain })}
            screeningAddress={screenMutation.variables?.address ?? null}
            loading={screenMutation.isPending}
          />
        </div>
      ),
    },
    {
      id: 'blockchain',
      label: fusionCopy.dock.blockchain,
      content: (
        <div className="p-3 space-y-2 fusion-text-data">
          <p className="fusion-text-micro">{fusionCopy.dock.supportedChains}</p>
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
          <p className="fusion-text-micro pt-2">{fusionCopy.dock.graphEdges}</p>
          <p>{graphQuery.data?.edges?.length ?? '—'}</p>
        </div>
      ),
    },
    {
      id: 'reports',
      label: fusionCopy.dock.reports,
      content: (
        <div className="p-2 [&_.enterprise-panel]:border-0">
          <FusionReportsPanel
            caseRef={caseRef}
            caseId={caseId}
            evidenceCount={workspaceQuery.data?.counts?.evidence}
            fusionResult={fusion ?? null}
          />
        </div>
      ),
    },
  ]
}
