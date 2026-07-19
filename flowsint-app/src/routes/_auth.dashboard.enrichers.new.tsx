import { createFileRoute, useRouterState, redirect } from '@tanstack/react-router'
import { TemplateEditor } from '@/components/templates/template-editor'
import { CONFIG } from '@/config'
import { FusionPlatformShell, FusionPlatformEditor } from '@/fusion'

export const Route = createFileRoute('/_auth/dashboard/enrichers/new')({
  beforeLoad: async () => {
    if (!CONFIG.ENRICHER_TEMPLATES_FEATURE_FLAG) {
      throw redirect({
        to: '/'
      })
    }
  },
  component: NewTemplatePage
})

function NewTemplatePage() {
  const routerState = useRouterState()
  const importedContent = (routerState.location.state as { importedContent?: string })
    ?.importedContent

  return (
    <FusionPlatformShell title="New enricher" subtitle="Template editor" activeSection="enrichers">
      <FusionPlatformEditor className="h-full min-h-[70vh]">
        <TemplateEditor importedYaml={importedContent} />
      </FusionPlatformEditor>
    </FusionPlatformShell>
  )
}
