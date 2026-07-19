import { createFileRoute } from '@tanstack/react-router'

import { FusionReportCenterPage } from '@/fusion/reports'
import type { ReportModuleId } from '@/fusion/reports/report-types'

export const Route = createFileRoute('/_auth/dashboard/fusion/reports/$caseRef/$reportType')({
  component: FusionReportModuleRoute,
})

function FusionReportModuleRoute() {
  const { caseRef, reportType } = Route.useParams()
  return (
    <FusionReportCenterPage
      caseRef={caseRef}
      reportType={reportType as ReportModuleId}
    />
  )
}
