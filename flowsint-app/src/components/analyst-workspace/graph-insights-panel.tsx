import { useQuery } from '@tanstack/react-query'

import { complianceService } from '@/api/compliance-service'
import { EnterprisePanel } from '@/components/enterprise/enterprise-ui'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { GitBranch } from 'lucide-react'
import { Link } from '@tanstack/react-router'

type Props = {
  caseId: string
}

export function GraphInsightsPanel({ caseId }: Props) {
  const graphQuery = useQuery({
    queryKey: ['compliance', 'case-graph-insights', caseId],
    queryFn: () => complianceService.getGraph(caseId),
    enabled: Boolean(caseId),
  })

  const graph = graphQuery.data
  const nodes = graph?.nodes?.length ?? 0
  const edges = graph?.edges?.length ?? 0
  const density = nodes > 1 ? (2 * edges) / (nodes * (nodes - 1)) : 0

  const typeCounts: Record<string, number> = {}
  for (const n of graph?.nodes ?? []) {
    const t = String((n as { type?: string }).type ?? 'unknown')
    typeCounts[t] = (typeCounts[t] ?? 0) + 1
  }

  return (
    <EnterprisePanel
      title="Graph Insights"
      description="Statistics from the existing case graph API — visualization unchanged."
    >
      {graphQuery.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <div className="space-y-4 text-sm">
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{nodes} nodes</Badge>
            <Badge variant="outline">{edges} edges</Badge>
            {nodes > 1 ? (
              <Badge variant="outline">density {density.toFixed(3)}</Badge>
            ) : null}
            <Badge variant="outline">avg degree {nodes ? ((2 * edges) / nodes).toFixed(1) : '0'}</Badge>
          </div>

          {Object.keys(typeCounts).length ? (
            <ul className="space-y-1 text-muted-foreground">
              {Object.entries(typeCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 8)
                .map(([type, count]) => (
                  <li key={type}>
                    {type}: <b>{count}</b>
                  </li>
                ))}
            </ul>
          ) : (
            <p className="text-muted-foreground flex items-center gap-2">
              <GitBranch className="h-4 w-4" />
              No graph nodes for this case yet.
            </p>
          )}

          <p className="text-xs text-muted-foreground">
            Full graph visualization:{' '}
            <Link to="/dashboard/compliance" className="text-primary underline">
              Compliance workspace
            </Link>
          </p>
        </div>
      )}
    </EnterprisePanel>
  )
}
