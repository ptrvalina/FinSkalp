import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { PlusIcon, FileCode2, Clock, FileX } from 'lucide-react'
import { useNavigate } from '@tanstack/react-router'
import { formatDistanceToNow } from 'date-fns'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import NewFlow from '@/components/flows/new-flow'
import { flowService } from '@/api/flow-service'
import ErrorState from '@/components/shared/error-state'
import { FusionPlatformShell, FusionEmptyState, FusionSkeleton } from '@/fusion'

interface Flow {
  id: string
  name: string
  description?: string
  category?: string[]
  created_at: string
  updated_at?: string
  flow_schema?: any
}

export const Route = createFileRoute('/_auth/dashboard/flows/')({
  component: FlowPage
})

function FlowPage() {
  const navigate = useNavigate()
  const {
    data: flows,
    isLoading,
    error,
    refetch
  } = useQuery<Flow[]>({
    queryKey: ['flow'],
    queryFn: () => flowService.get()
  })

  const categories =
    flows?.reduce((acc: string[], flow) => {
      if (flow.category) {
        flow.category.forEach((cat) => {
          if (!acc.includes(cat)) acc.push(cat)
        })
      }
      return acc
    }, []) || []

  const allCategories = ['All', ...categories, 'Uncategorized']

  return (
    <FusionPlatformShell
      title="Архитектор потоков"
      subtitle="Операционные пайплайны обогащения и триажа"
      activeSection="flows"
      actions={
        <NewFlow>
          <Button size="sm" variant="outline" className="fusion-text-micro h-7" data-tour-id="create-flow">
            <PlusIcon className="w-3 h-3 mr-1" />
            Новый поток
          </Button>
        </NewFlow>
      }
    >
      {isLoading ? (
        <FusionSkeleton rows={6} variant="row" />
      ) : error ? (
        <ErrorState
          title="Couldn't load flows"
          description="Something went wrong while fetching data. Please try again."
          error={error}
          onRetry={() => refetch()}
        />
      ) : !flows?.length ? (
        <FusionEmptyState
          title="Нет потоков"
          description="Создайте операционный пайплайн обогащения для Mission Control."
          icon={<FileX />}
          action={
            <NewFlow>
              <Button size="sm">
                <PlusIcon className="w-4 h-4 mr-2" />
                Создать поток
              </Button>
            </NewFlow>
          }
        />
      ) : (
        <Tabs defaultValue="All" className="space-y-4">
          <TabsList className="h-auto bg-[var(--fusion-bg-panel)] border border-[var(--fusion-border)]">
            {allCategories.map((category) => (
              <TabsTrigger key={category} value={category} className="fusion-text-micro">
                {category}
              </TabsTrigger>
            ))}
          </TabsList>

          {allCategories.map((category) => (
            <TabsContent key={category} value={category} className="mt-0">
              <div className="divide-y divide-[var(--fusion-border)] border border-[var(--fusion-border)] rounded-[var(--fusion-radius-sm)]">
                {flows
                  ?.filter((flow) =>
                    category === 'All'
                      ? true
                      : category === 'Uncategorized'
                        ? !flow.category?.length
                        : flow.category?.includes(category)
                  )
                  .map((flow) => (
                    <button
                      key={flow.id}
                      type="button"
                      className="w-full flex items-center justify-between gap-3 px-3 py-2 text-left hover:bg-[var(--fusion-bg-interactive)] transition-colors"
                      onClick={() => navigate({ to: `/dashboard/flows/${flow.id}` })}
                      data-tour-id="flow-list"
                    >
                      <div className="min-w-0">
                        <p className="fusion-text-data truncate">{flow.name || '(Unnamed flow)'}</p>
                        <p className="fusion-text-micro truncate text-[var(--fusion-text-tertiary)]">
                          {flow.description || '—'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="fusion-text-micro text-[var(--fusion-text-tertiary)] inline-flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDistanceToNow(new Date(flow.updated_at || flow.created_at), { addSuffix: true })}
                        </span>
                        <FileCode2 className="w-3.5 h-3.5 text-[var(--fusion-text-tertiary)]" />
                      </div>
                    </button>
                  ))}
              </div>
            </TabsContent>
          ))}
        </Tabs>
      )}
    </FusionPlatformShell>
  )
}
