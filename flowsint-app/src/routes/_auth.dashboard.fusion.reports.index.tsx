import { createFileRoute } from '@tanstack/react-router'

import { FusionReportCenterPage } from '@/fusion/reports'

export const Route = createFileRoute('/_auth/dashboard/fusion/reports/')({
  component: FusionReportsHubRoute,
})

function FusionReportsHubRoute() {
  return <FusionReportCenterPage />
}
