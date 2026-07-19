import { createFileRoute, Outlet } from '@tanstack/react-router'
import { investigationService } from '@/api/investigation-service'

function InvestigationSkeleton() {
  return (
    <div className="h-full w-full bg-[var(--fusion-bg-void)] flex items-center justify-center">
      <div className="w-6 h-6 border-2 border-[var(--fusion-ops-blue)] border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

export const Route = createFileRoute('/_auth/dashboard/investigations/$investigationId')({
  loader: async ({ params: { investigationId } }) => {
    const investigation = await investigationService.getById(investigationId)
    return { investigation }
  },
  component: () => <Outlet />,
  pendingComponent: InvestigationSkeleton
})
