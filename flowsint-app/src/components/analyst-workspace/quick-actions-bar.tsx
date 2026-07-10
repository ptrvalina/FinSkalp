import { Button } from '@/components/ui/button'
import { FileText, GitBranch, Search, Shield, Sparkles } from 'lucide-react'

type Props = {
  onAction: (actionId: string) => void
}

const ACTIONS = [
  { id: 'open_evidence', label: 'Доказательства', icon: Shield },
  { id: 'open_graph', label: 'Граф', icon: GitBranch },
  { id: 'open_reports', label: 'Отчёты', icon: FileText },
  { id: 'ask_ai', label: 'AI', icon: Sparkles },
  { id: 'search_entity', label: 'Поиск', icon: Search },
] as const

export function QuickActionsBar({ onAction }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {ACTIONS.map(({ id, label, icon: Icon }) => (
        <Button key={id} size="sm" variant="outline" className="gap-1.5" onClick={() => onAction(id)}>
          <Icon className="h-3.5 w-3.5" />
          {label}
        </Button>
      ))}
    </div>
  )
}
