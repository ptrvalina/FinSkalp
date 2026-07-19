# Investigation Workspace

## Route

`/dashboard/fusion/investigation/:caseRef`

## Boot Sequence

1. Resolve `caseRef` → `caseId` via `listCases`
2. Parallel fetch: `getCase`, `getGraph`, `getCaseTimeline`, `getAnalystWorkspaceState`, `getWorkflowRecommendations`
3. Mount `FusionGraphStage` immediately (loading state inside stage)
4. Hydrate mission strip from case + workspace state
5. Subscribe SSE via `useComplianceEvents`

## Layout (default)

| Region | Component | Data |
|--------|-----------|------|
| Rail | FusionRail | Navigation |
| Strip | FusionMissionStrip | 14 fields |
| Left | FusionPanel → Timeline | `getCaseTimeline` |
| Center | FusionGraphStage | `getGraph` + alerts |
| Right | FusionMIO | `getWorkflowRecommendations` |
| Bottom | FusionDock | Evidence, wallets, reports |

## Dock Tabs

| Tab | Source |
|-----|--------|
| Evidence | `getAnalystWorkspaceState().evidence` |
| Wallets | Case fusion_result / screen actions |
| Reports | `listReports(caseRef)` |
| OSINT | Evidence items filtered `source_type=osint` |

## Case Switch

Queue click navigates to new `:caseRef`. Graph stage updates data props — **does not unmount**.

## STR Pipeline Display

`FusionMissionStrip` field `STATUS` shows human workflow label mapped from `workflow_status`:

```
new → НОВЫЙ STR
scoring → СКОРИНГ
fusion → OSINT FUSION
graph → ГРАФ СВЯЗЕЙ
...
```

## Exit

Rail COMMAND → `/dashboard/fusion` (graph unmounts — command center only)
