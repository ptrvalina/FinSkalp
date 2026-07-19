import { createFileRoute } from '@tanstack/react-router'

import { FusionReportCenterPage } from '@/fusion/reports'

export const Route = createFileRoute('/_auth/dashboard/fusion/reports/$caseRef/')({
  component: FusionReportCaseModulesRoute,
})

function FusionReportCaseModulesRoute() {
  const { caseRef } = Route.useParams()
  return <FusionReportCenterPage caseRef={caseRef} />
}
