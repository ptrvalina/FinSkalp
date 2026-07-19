import { createFileRoute } from '@tanstack/react-router'

import { fusionLensFromSearch } from '@/fusion/fusion-route-search'
import { FusionMissionControlWorkspace } from '@/fusion/mission-control/FusionMissionControlWorkspace'

import type { FusionOpsLens } from '@/fusion/FusionRail'

export const Route = createFileRoute('/_auth/dashboard/fusion/')({
  component: FusionMissionControlRoute,
})

function FusionMissionControlRoute() {
  const search = Route.useSearch() as { lens?: FusionOpsLens }
  return <FusionMissionControlWorkspace lensSearch={fusionLensFromSearch(search.lens)} />
}
