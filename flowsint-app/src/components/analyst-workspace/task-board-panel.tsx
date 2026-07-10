import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { complianceService } from '@/api/compliance-service'
import { EnterprisePanel } from '@/components/enterprise/enterprise-ui'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Briefcase } from 'lucide-react'

const COLUMNS = [
  { id: 'new', label: 'Новые' },
  { id: 'in_progress', label: 'В работе' },
  { id: 'review', label: 'На проверке' },
  { id: 'closed', label: 'Закрыты' },
] as const

export function TaskBoardPanel() {
  const queryClient = useQueryClient()

  const casesQuery = useQuery({
    queryKey: ['compliance', 'cases-all'],
    queryFn: () => complianceService.listCases(),
    staleTime: 30_000,
  })

  const statsQuery = useQuery({
    queryKey: ['compliance', 'workflow-stats'],
    queryFn: () => complianceService.getWorkflowStats(),
    staleTime: 60_000,
  })

  const transitionMutation = useMutation({
    mutationFn: ({ caseId, status }: { caseId: string; status: string }) =>
      complianceService.transitionCase(caseId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance', 'cases-all'] })
      queryClient.invalidateQueries({ queryKey: ['compliance', 'workflow-stats'] })
    },
  })

  const cases = casesQuery.data ?? []

  return (
    <EnterprisePanel
      title="Task Board"
      description="Workflow cases via existing compliance API — no duplicate store"
    >
      {casesQuery.isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : (
        <div className="space-y-4">
          {statsQuery.data ? (
            <div className="flex flex-wrap gap-2 text-xs">
              <Badge variant="outline">Всего: {statsQuery.data.total}</Badge>
              {statsQuery.data.pipeline
                ? Object.entries(statsQuery.data.pipeline).map(([k, v]) => (
                    <Badge key={k} variant="secondary">
                      {k}: {v}
                    </Badge>
                  ))
                : null}
            </div>
          ) : null}

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {COLUMNS.map((col) => {
              const colCases = cases.filter((c) => c.workflow_status === col.id)
              return (
                <div
                  key={col.id}
                  className="rounded-md border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] p-2 min-h-[120px]"
                >
                  <p className="text-xs font-medium mb-2 flex items-center gap-1">
                    <Briefcase className="h-3 w-3" />
                    {col.label} ({colCases.length})
                  </p>
                  <div className="space-y-2">
                    {colCases.slice(0, 5).map((c) => (
                      <div key={c.id} className="rounded border bg-background p-2 text-xs">
                        <p className="font-mono truncate">{c.case_ref}</p>
                        <p className="text-muted-foreground truncate">{c.status}</p>
                        {col.id !== 'closed' ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 mt-1 text-[10px] px-2"
                            disabled={transitionMutation.isPending}
                            onClick={() =>
                              transitionMutation.mutate({
                                caseId: c.id,
                                status:
                                  col.id === 'new'
                                    ? 'in_progress'
                                    : col.id === 'in_progress'
                                      ? 'review'
                                      : 'closed',
                              })
                            }
                          >
                            Advance →
                          </Button>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </EnterprisePanel>
  )
}
