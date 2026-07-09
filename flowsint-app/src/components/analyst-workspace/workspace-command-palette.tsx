import { useEffect, useState } from 'react'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command'
import { complianceService } from '@/api/compliance-service'

type CommandDef = {
  id: string
  label_ru: string
  shortcut?: string
  level?: string
}

type SearchResult = {
  id: string
  kind: string
  display_name?: string
  canonical_key?: string
  entity_type?: string
  case_ref?: string
}

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  commands?: CommandDef[]
  onCommand: (commandId: string) => void
  caseRef?: string | null
  onSearchSelect?: (result: SearchResult) => void
}

const FALLBACK_COMMANDS: CommandDef[] = [
  { id: 'open_summary', label_ru: 'Открыть сводку', shortcut: 'Ctrl+1', level: 'contextual' },
  { id: 'open_timeline', label_ru: 'Открыть хронологию', shortcut: 'Ctrl+4', level: 'contextual' },
  { id: 'open_evidence', label_ru: 'Открыть доказательства', shortcut: 'Ctrl+5', level: 'contextual' },
  { id: 'search_entity', label_ru: 'Найти сущность', shortcut: 'Ctrl+K', level: 'global' },
  { id: 'open_compliance', label_ru: 'Открыть комплаенс', level: 'global' },
]

const KIND_LABELS: Record<string, string> = {
  case: 'Дело',
  entity: 'Сущность',
  evidence: 'Доказательство',
}

export function WorkspaceCommandPalette({
  open,
  onOpenChange,
  commands,
  onCommand,
  caseRef,
  onSearchSelect,
}: Props) {
  const list = commands?.length ? commands : FALLBACK_COMMANDS
  const contextual = list.filter((c) => c.level === 'contextual')
  const global = list.filter((c) => c.level !== 'contextual')
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    if (!open) {
      setQuery('')
      setSearchResults([])
    }
  }, [open])

  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setSearchResults([])
      return
    }
    let cancelled = false
    const timer = setTimeout(async () => {
      setSearching(true)
      try {
        const res = await complianceService.searchAnalystWorkspace({
          query: trimmed,
          caseRef: caseRef ?? undefined,
        })
        if (!cancelled && res.ok) {
          setSearchResults(res.results)
        }
      } catch {
        if (!cancelled) setSearchResults([])
      } finally {
        if (!cancelled) setSearching(false)
      }
    }, 250)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [query, caseRef])

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Палитра команд"
      description="Быстрые действия и универсальный поиск"
    >
      <CommandInput
        placeholder="Команда или поиск по делу…"
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        <CommandEmpty>{searching ? 'Поиск…' : 'Команда не найдена'}</CommandEmpty>
        {searchResults.length > 0 ? (
          <CommandGroup heading="Результаты поиска">
            {searchResults.map((item) => (
              <CommandItem
                key={`${item.kind}-${item.id}`}
                value={`${KIND_LABELS[item.kind] ?? item.kind} ${item.display_name ?? item.canonical_key ?? item.id}`}
                onSelect={() => {
                  onSearchSelect?.(item)
                  onOpenChange(false)
                }}
              >
                <span className="text-xs text-muted-foreground mr-2">
                  {KIND_LABELS[item.kind] ?? item.kind}
                </span>
                <span className="truncate">
                  {item.display_name ?? item.canonical_key ?? item.id}
                </span>
              </CommandItem>
            ))}
          </CommandGroup>
        ) : null}
        {contextual.length > 0 ? (
          <CommandGroup heading="Контекст расследования">
            {contextual.map((cmd) => (
              <CommandItem
                key={cmd.id}
                value={cmd.label_ru}
                onSelect={() => {
                  onCommand(cmd.id)
                  onOpenChange(false)
                }}
              >
                <span>{cmd.label_ru}</span>
                {cmd.shortcut ? (
                  <span className="ml-auto text-xs text-muted-foreground">{cmd.shortcut}</span>
                ) : null}
              </CommandItem>
            ))}
          </CommandGroup>
        ) : null}
        {global.length > 0 ? (
          <>
            <CommandSeparator />
            <CommandGroup heading="Глобальные">
              {global.map((cmd) => (
                <CommandItem
                  key={cmd.id}
                  value={cmd.label_ru}
                  onSelect={() => {
                    onCommand(cmd.id)
                    onOpenChange(false)
                  }}
                >
                  <span>{cmd.label_ru}</span>
                  {cmd.shortcut ? (
                    <span className="ml-auto text-xs text-muted-foreground">{cmd.shortcut}</span>
                  ) : null}
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        ) : null}
      </CommandList>
    </CommandDialog>
  )
}
