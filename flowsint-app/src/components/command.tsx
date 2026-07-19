import * as React from 'react'
import { Fingerprint, Search, Workflow, FileText, Waypoints } from 'lucide-react'

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator
} from '@/components/ui/command'
import { useKeyboardShortcut } from '@/hooks/use-keyboard-shortcut'
import { Button } from './ui/button'
import { useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { investigationService } from '@/api/investigation-service'
import { analysisService } from '@/api/analysis-service'
import { type Investigation } from '@/types/investigation'
import { type Analysis } from '@/types'
import { Skeleton } from './ui/skeleton'

// Skeleton component for command palette loading
function CommandSkeleton() {
  return (
    <div className="space-y-2 p-2">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="flex items-center gap-2 p-2 rounded-md">
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-4 flex-1" />
        </div>
      ))}
    </div>
  )
}

export function Command() {
  const [open, setOpen] = React.useState(false)
  const [searchQuery, setSearchQuery] = React.useState('')
  const navigate = useNavigate()

  // Fetch investigations when dialog opens
  const { data: investigations = [], isLoading: isLoadingInvestigations } = useQuery({
    queryKey: ['command-investigations'],
    queryFn: investigationService.get,
    enabled: open // Only fetch when dialog is open
  })

  // Fetch all analyses when dialog opens
  const { data: allAnalyses = [], isLoading: isLoadingAnalyses } = useQuery({
    queryKey: ['command-analyses'],
    queryFn: analysisService.get,
    enabled: open // Only fetch when dialog is open
  })

  useKeyboardShortcut({
    key: 'k',
    ctrlOrCmd: true,
    callback: () => {
      setOpen((prev) => !prev)
    }
  })

  // Filter investigations and analyses based on search query
  const filteredData = React.useMemo(() => {
    if (!searchQuery.trim()) {
      return { investigations, analyses: allAnalyses }
    }

    const query = searchQuery.toLowerCase().trim()

    const filteredInvestigations = investigations.filter((investigation: Investigation) => {
      const matchesName = investigation.name.toLowerCase().includes(query)
      const matchesDescription = investigation.description?.toLowerCase().includes(query)
      const matchesSketches = investigation.sketches?.some((sketch) =>
        sketch.title.toLowerCase().includes(query)
      )
      // Check if any analyses in this investigation match the query
      const investigationAnalyses = allAnalyses.filter(
        (analysis: Analysis) => analysis.investigation_id === investigation.id
      )
      const matchesAnalyses = investigationAnalyses.some(
        (analysis: Analysis) =>
          analysis.title.toLowerCase().includes(query) ||
          analysis.description?.toLowerCase().includes(query)
      )
      return matchesName || matchesDescription || matchesSketches || matchesAnalyses
    })

    // Filter analyses to only include those from filtered investigations
    const filteredAnalyses = allAnalyses.filter((analysis: Analysis) => {
      const matchesTitle = analysis.title.toLowerCase().includes(query)
      const matchesDescription = analysis.description?.toLowerCase().includes(query)
      const belongsToFilteredInvestigation = filteredInvestigations.some(
        (inv: Investigation) => inv.id === analysis.investigation_id
      )
      return (matchesTitle || matchesDescription) && belongsToFilteredInvestigation
    })

    return { investigations: filteredInvestigations, analyses: filteredAnalyses }
  }, [investigations, allAnalyses, searchQuery])

  // Group analyses by investigation for display
  const analysesByInvestigation = React.useMemo(() => {
    const grouped: Record<string, Analysis[]> = {}
    filteredData.analyses.forEach((analysis: Analysis) => {
      if (analysis.investigation_id) {
        if (!grouped[analysis.investigation_id]) {
          grouped[analysis.investigation_id] = []
        }
        grouped[analysis.investigation_id].push(analysis)
      }
    })
    return grouped
  }, [filteredData.analyses])

  const isLoading = isLoadingInvestigations || isLoadingAnalyses

  return (
    <>
      <Button
        variant="ghost"
        onClick={() => setOpen(true)}
        className="h-9 w-full min-w-[14rem] max-w-xs rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-deck)] px-3 text-xs text-[var(--fusion-text-secondary)] hover:border-[var(--fusion-border-strong)] hover:bg-[var(--fusion-bg-interactive)]"
      >
        <span className="flex items-center gap-2">
          <Search className="h-4 w-4" /> Command Palette
        </span>
        <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-panel)] px-1.5 font-mono text-[10px] font-medium text-[var(--fusion-text-tertiary)] opacity-100">
          <span className="text-xs">⌘</span>K
        </kbd>
      </Button>
      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput
          placeholder="Open case, search wallet, build graph, import evidence..."
          value={searchQuery}
          onValueChange={setSearchQuery}
        />
        <CommandList>
          {isLoading ? (
            <CommandSkeleton />
          ) : (
            <>
              {filteredData.investigations.length === 0 && filteredData.analyses.length === 0 ? (
                <CommandEmpty>No results found.</CommandEmpty>
              ) : (
                <>
                  {filteredData.investigations.length > 0 && (
                    <CommandGroup heading="Investigations">
                      {filteredData.investigations.map((investigation: Investigation) => (
                        <React.Fragment key={investigation.id}>
                          <CommandItem
                            onSelect={() => {
                              navigate({
                                to: '/dashboard/investigations/$investigationId',
                                params: { investigationId: investigation.id }
                              })
                              setOpen(false)
                            }}
                          >
                            <div className="flex items-center gap-2">
                              <Fingerprint className="h-4 w-4" />
                              <span className="flex-1">{investigation.name}</span>
                            </div>
                          </CommandItem>

                          {/* Show sketches for this investigation */}
                          {investigation.sketches?.map((sketch) => (
                            <CommandItem
                              key={sketch.id}
                              onSelect={() => {
                                navigate({
                                  to: '/dashboard/investigations/$investigationId/$type/$id',
                                  params: {
                                    investigationId: investigation.id,
                                    type: 'graph',
                                    id: sketch.id
                                  }
                                })
                                setOpen(false)
                              }}
                            >
                              <div className="flex items-center gap-2 pl-6">
                                <Waypoints className="h-4 w-4" />
                                <span className="flex-1">{sketch.title}</span>
                              </div>
                            </CommandItem>
                          ))}

                          {/* Show analyses for this investigation */}
                          {analysesByInvestigation[investigation.id]?.map((analysis) => (
                            <CommandItem
                              key={analysis.id}
                              onSelect={() => {
                                navigate({
                                  to: '/dashboard/investigations/$investigationId/$type/$id',
                                  params: {
                                    investigationId: investigation.id,
                                    type: 'analysis',
                                    id: analysis.id
                                  }
                                })
                                setOpen(false)
                              }}
                            >
                              <div className="flex items-center gap-2 pl-6">
                                <FileText className="h-4 w-4" />
                                <span className="flex-1">{analysis.title}</span>
                              </div>
                            </CommandItem>
                          ))}
                        </React.Fragment>
                      ))}
                    </CommandGroup>
                  )}

                  <CommandSeparator />
                  <CommandGroup heading="Quick Actions">
                    <CommandItem
                      onSelect={() => {
                        navigate({ to: '/dashboard' })
                        setOpen(false)
                      }}
                    >
                      <div className="flex items-center gap-2">
                        <Fingerprint className="h-4 w-4" />
                        <span>All Investigations</span>
                      </div>
                    </CommandItem>
                    <CommandItem
                      onSelect={() => {
                        navigate({ to: '/dashboard/flows' })
                        setOpen(false)
                      }}
                    >
                      <div className="flex items-center gap-2">
                        <Workflow className="h-4 w-4" />
                          <span>Open Flow Architect</span>
                      </div>
                    </CommandItem>
                    <CommandItem
                      onSelect={() => {
                        navigate({ to: '/dashboard/compliance', search: { caseRef: undefined } })
                        setOpen(false)
                      }}
                    >
                      <div className="flex items-center gap-2">
                        <Fingerprint className="h-4 w-4" />
                        <span>Open compliance lifecycle</span>
                      </div>
                    </CommandItem>
                  </CommandGroup>
                </>
              )}
            </>
          )}
        </CommandList>
      </CommandDialog>
    </>
  )
}
