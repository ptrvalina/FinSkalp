import { Command } from '../command'
import { Link, useNavigate, useParams } from '@tanstack/react-router'
import InvestigationSelector from './investigation-selector'
import SketchSelector from './sketch-selector'
import { memo, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Switch } from '../ui/switch'
import { Label } from '../ui/label'
import { useLayoutStore } from '@/stores/layout-store'
import { Button } from '@/components/ui/button'
import { AvatarGroup } from '@/components/ui/avatar'
import { investigationService } from '@/api/investigation-service'
import { queryKeys } from '@/api/query-keys'
import type { Collaborator } from '@/types'
import { ImportSheet } from '../sketches/import-sheet'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { Settings2, Upload } from 'lucide-react'
import { isMac } from '@/lib/utils'
import { useGraphSettingsStore } from '@/stores/graph-settings-store'
import { useMutation } from '@tanstack/react-query'
import { Separator } from '../ui/separator'
import { useConfirm } from '../use-confirm-dialog'
import { sketchService } from '@/api/sketch-service'
import { toast } from 'sonner'
import { useKeyboardShortcut } from '@/hooks/use-keyboard-shortcut'
import { usePermissions } from '@/hooks/use-can'
import { Badge } from '../ui/badge'
import { Bell } from 'lucide-react'
import { NavUser } from '../nav-user'

export const TopNavbar = memo(() => {
  const { investigationId, id, type } = useParams({ strict: false })
  const toggleAnalysis = useLayoutStore((s) => s.toggleAnalysis)
  const isOpenAnalysis = useLayoutStore((s) => s.isOpenAnalysis)

  const { data: collaborators = [] } = useQuery<Collaborator[]>({
    queryKey: queryKeys.investigations.collaborators(investigationId!),
    queryFn: () => investigationService.getCollaborators(investigationId!),
    enabled: !!investigationId
  })

  const handleToggleAnalysis = useCallback(() => toggleAnalysis(), [toggleAnalysis])

  return (
    <header
      className="flex h-14 shrink-0 items-center gap-4 border-b border-[var(--fs-border)] bg-[var(--fs-bg-primary)] px-4"
      data-tour-id="navigation"
    >
      <div className="flex min-w-0 items-center gap-4">
        <Link to="/dashboard" className="flex items-center gap-3">
          <img src="/icon.png" alt="FinSkalp" className="h-8 w-8" />
          <div className="min-w-0">
            <span className="block truncate text-sm font-semibold tracking-[0.08em] text-[var(--fs-text-primary)]">
              FinSkalp
            </span>
            <span className="block text-[11px] uppercase tracking-[0.16em] text-[var(--fs-text-tertiary)]">
              Sovereign Investigation Platform
            </span>
          </div>
        </Link>
        <div className="hidden items-center gap-2 xl:flex">
          {investigationId && <InvestigationSelector />}
          {id && (
            <>
              <span className="text-sm opacity-30">/</span>
              <SketchSelector />
            </>
          )}
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center">
        <div className="w-full max-w-md">
          <Command />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Badge className="hidden rounded-sm border border-[var(--fs-border)] bg-[var(--fs-surface)] px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-[var(--fs-accent)] md:inline-flex">
          Self-hosted
        </Badge>
        {investigationId && collaborators.length > 0 ? (
          <>
            <AvatarGroup users={collaborators.map((c) => c.user)} size="sm" max={5} />
            <Separator orientation="vertical" className="h-5" />
          </>
        ) : null}
        <div className="flex items-center space-x-2">
          {type === 'graph' && (
            <>
              <Switch checked={isOpenAnalysis} onCheckedChange={handleToggleAnalysis} id="notes" />
              <Label htmlFor="notes">
                Toggle notes
                <span className="text-[.7rem] -ml-1 opacity-60">({isMac ? '⌘' : 'ctrl'}L)</span>
              </Label>
            </>
          )}
        </div>
        <Button
          size="icon"
          variant="ghost"
          className="h-9 w-9 rounded-sm border border-[var(--fs-border)] text-[var(--fs-text-secondary)]"
        >
          <Bell className="h-4 w-4" />
        </Button>
        {id && <InvestigationMenu investigationId={investigationId} sketchId={id} />}
        <NavUser />
      </div>
    </header>
  )
})

export function InvestigationMenu({
  investigationId,
  sketchId
}: {
  investigationId?: string
  sketchId: string
}) {
  const { canEdit } = usePermissions()
  const toggleSettingsModal = useGraphSettingsStore((s) => s.toggleSettingsModal)
  const toggleKeyboardShortcutsModal = useGraphSettingsStore((s) => s.toggleKeyboardShortcutsModal)
  const setImportModalOpen = useGraphSettingsStore((s) => s.setImportModalOpen)
  const navigate = useNavigate()
  const { confirm } = useConfirm()

  useKeyboardShortcut({
    key: 'g',
    ctrlOrCmd: true,
    callback: toggleSettingsModal
  })

  useKeyboardShortcut({
    key: 'k',
    ctrlOrCmd: true,
    callback: toggleKeyboardShortcutsModal
  })

  // Delete sketch mutation
  const deleteSketchMutation = useMutation({
    mutationFn: sketchService.delete,
    onSuccess: () => {
      investigationId &&
        navigate({
          to: '/dashboard/investigations/$investigationId',
          params: {
            investigationId: investigationId as string
          }
        })
    },
    onError: (error) => {
      console.error('Error deleting sketch:', error)
    }
  })

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()

    const confirmed = await confirm({
      title: 'Delete Sketch',
      message: `Are you sure you want to delete this sketch ? This action cannot be undone.`
    })

    if (confirmed) {
      toast.promise(deleteSketchMutation.mutateAsync(sketchId), {
        loading: 'Deleting sketch...',
        success: () => `Sketch has been deleted`,
        error: 'Failed to delete sketch'
      })
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <div>
          <Button size="icon" variant="ghost">
            <Settings2 />
          </Button>
        </div>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56" align="start">
        <DropdownMenuLabel>Settings</DropdownMenuLabel>
        <DropdownMenuGroup>
          <DropdownMenuItem onClick={toggleSettingsModal}>
            General
            <DropdownMenuShortcut>⌘G</DropdownMenuShortcut>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={toggleKeyboardShortcutsModal}>
            Keyboard shortcuts
            <DropdownMenuShortcut>⌘K</DropdownMenuShortcut>
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem>
          <a className="h-full w-full" target="_blank" href="https://github.com/reconurge/flowsint">
            GitHub
          </a>
        </DropdownMenuItem>
        <DropdownMenuItem>
          <a
            className="h-full w-full"
            target="_blank"
            href="https://github.com/reconurge/flowsint/issues"
          >
            Support
          </a>
        </DropdownMenuItem>
        <DropdownMenuItem disabled>API</DropdownMenuItem>
        {canEdit && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setImportModalOpen(true)}>
              <Upload /> Import entities
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleDelete} variant="destructive">
              Delete sketch
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
      {canEdit && <ImportSheet sketchId={sketchId} />}
    </DropdownMenu>
  )
}
