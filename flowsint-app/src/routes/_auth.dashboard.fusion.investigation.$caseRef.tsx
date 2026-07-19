import { createFileRoute } from '@tanstack/react-router'

import { fusionLensFromSearch } from '@/fusion/fusion-route-search'
import { FusionInvestigationWorkspace } from '@/fusion/investigation/FusionInvestigationWorkspace'

import type { FusionOpsLens } from '@/fusion/FusionRail'

export const Route = createFileRoute('/_auth/dashboard/fusion/investigation/$caseRef')({
  component: FusionInvestigationRoute,
})

function FusionInvestigationRoute() {
  const { caseRef } = Route.useParams()
  const search = Route.useSearch() as { lens?: FusionOpsLens }
  return (
    <FusionInvestigationWorkspace
      caseRef={caseRef}
      lensSearch={fusionLensFromSearch(search.lens)}
    />
  )
}
