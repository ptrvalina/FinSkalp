import { useState, useEffect, useRef, type ReactNode, type RefObject } from 'react'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import type { ImperativePanelHandle } from 'react-resizable-panels'
import { cn } from '@/lib/utils'

export type FusionDockTab = {
  id: string
  label: string
  content: ReactNode
}

type Props = {
  tabs: FusionDockTab[]
  defaultTab?: string
  activeTab?: string
  onTabChange?: (tabId: string) => void
  className?: string
  collapsible?: boolean
  /** When wrapped by a parent ResizablePanel (FusionCanvasOS / FusionDockLayout). */
  panelRef?: RefObject<ImperativePanelHandle | null>
  collapsed?: boolean
  onCollapsedChange?: (collapsed: boolean) => void
}

export function FusionDock({
  tabs,
  defaultTab,
  activeTab: activeTabProp,
  onTabChange,
  className,
  collapsible = true,
  panelRef,
  collapsed: collapsedProp,
  onCollapsedChange,
}: Props) {
  const [internalTab, setInternalTab] = useState(defaultTab ?? tabs[0]?.id ?? '')
  const [internalCollapsed, setInternalCollapsed] = useState(false)
  const collapsed = collapsedProp ?? internalCollapsed
  const setCollapsed = (next: boolean) => {
    onCollapsedChange?.(next)
    if (collapsedProp == null) setInternalCollapsed(next)
  }
  const activeTab = activeTabProp ?? internalTab
  const setActiveTab = (id: string) => {
    if (onTabChange) onTabChange(id)
    else setInternalTab(id)
    if (collapsed) panelRef?.current?.expand()
  }

  useEffect(() => {
    if (activeTabProp) setInternalTab(activeTabProp)
  }, [activeTabProp])

  const active = tabs.find((t) => t.id === activeTab) ?? tabs[0]

  const toggleCollapse = () => {
    if (panelRef?.current) {
      if (collapsed) panelRef.current.expand()
      else panelRef.current.collapse()
      return
    }
    setCollapsed(!collapsed)
  }

  if (!tabs.length) return null

  return (
    <div
      data-fusion-dock
      data-fusion-dock-collapsed={collapsed ? 'true' : undefined}
      className={cn(
        'fusion-dock-layout__dock flex h-full min-h-0 flex-col fusion-surface-panel',
        collapsed && 'fusion-dock-layout__dock--collapsed',
        className
      )}
    >
      <div className="fusion-dock-tabs" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={tab.id === activeTab}
            aria-label={`${tab.label} tab`}
            className={cn(
              'fusion-dock-tab',
              tab.id === activeTab && 'fusion-dock-tab--active'
            )}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
        {collapsible ? (
          <button
            type="button"
            className="fusion-dock-collapse ml-auto"
            onClick={toggleCollapse}
            aria-expanded={!collapsed}
            aria-label={collapsed ? 'Expand dock' : 'Collapse dock'}
            title={collapsed ? 'Развернуть dock' : 'Свернуть dock'}
          >
            {collapsed ? '▲' : '▼'}
          </button>
        ) : null}
      </div>
      {!collapsed ? (
        <div className="fusion-panel__body min-h-0 flex-1 overflow-auto" role="tabpanel">
          {active?.content}
        </div>
      ) : null}
    </div>
  )
}

type ResizableProps = Props & {
  defaultSize?: number
  minSize?: number
}

/** Dock panel for vertical ResizablePanelGroup layouts. */
export function FusionDockResizable({
  defaultSize = 22,
  minSize = 8,
  collapsible = true,
  ...dockProps
}: ResizableProps) {
  const panelRef = useRef<ImperativePanelHandle>(null)
  const [collapsed, setCollapsed] = useState(false)

  if (!dockProps.tabs.length) return null

  return (
    <ResizablePanel
      ref={panelRef}
      id="fusion-dock"
      order={2}
      defaultSize={defaultSize}
      minSize={minSize}
      collapsible={collapsible}
      collapsedSize={4}
      onCollapse={() => setCollapsed(true)}
      onExpand={() => setCollapsed(false)}
      className={cn('min-h-0', collapsed && 'fusion-dock-layout__dock--collapsed')}
    >
      <FusionDock {...dockProps} panelRef={panelRef} collapsible={collapsible} />
    </ResizablePanel>
  )
}

type DockLayoutProps = {
  main: ReactNode
  dock: ReactNode
  autoSaveId?: string
  defaultDockSize?: number
}

export function FusionDockLayout({
  main,
  dock,
  autoSaveId = 'fusion-inv-dock-layout',
  defaultDockSize = 22,
}: DockLayoutProps) {
  return (
    <ResizablePanelGroup
      direction="vertical"
      autoSaveId={autoSaveId}
      className="h-full min-h-0"
    >
      <ResizablePanel id="fusion-main" order={1} defaultSize={100 - defaultDockSize} minSize={50}>
        {main}
      </ResizablePanel>
      <ResizableHandle className="fusion-dock-handle" />
      {dock}
    </ResizablePanelGroup>
  )
}
