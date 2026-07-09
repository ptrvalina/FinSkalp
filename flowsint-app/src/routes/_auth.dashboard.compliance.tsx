import { createFileRoute } from '@tanstack/react-router'
import { CompliancePage } from '@/components/compliance/compliance-page'

export const Route = createFileRoute('/_auth/dashboard/compliance')({
  component: CompliancePage
})
