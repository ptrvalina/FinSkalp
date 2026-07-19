import { createFileRoute } from '@tanstack/react-router'
import Editor from '@/components/flows/editor'
import Loader from '@/components/loader'
import { flowService } from '@/api/flow-service'
import { FusionPlatformShell, FusionPlatformEditor } from '@/fusion'

export const Route = createFileRoute('/_auth/dashboard/flows/$flowId')({
  loader: async ({ params: { flowId } }) => {
    return {
      flow: await flowService.getById(flowId)
    }
  },
  component: FlowPage,
  pendingComponent: () => (
    <div className="h-full w-full flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <Loader />
        <p className="text-muted-foreground">Loading flow...</p>
      </div>
    </div>
  ),
  errorComponent: ({ error }) => (
    <div className="h-full w-full flex items-center justify-center">
      <div className="text-center">
        <h2 className="text-lg font-semibold text-destructive mb-2">Error loading flow</h2>
        <p className="text-muted-foreground">{error.message}</p>
      </div>
    </div>
  )
})

function FlowPage() {
  const { flow } = Route.useLoaderData()
  return (
    <FusionPlatformShell
      title={flow.name ?? 'Flow Architect'}
      subtitle={flow.description ?? 'Pipeline editor'}
      activeSection="flows"
    >
      <FusionPlatformEditor className="h-full min-h-[70vh]">
        <Editor
          key={flow.id}
          flow={flow}
          initialNodes={flow?.flow_schema?.nodes}
          initialEdges={flow?.flow_schema?.edges}
        />
      </FusionPlatformEditor>
    </FusionPlatformShell>
  )
}
