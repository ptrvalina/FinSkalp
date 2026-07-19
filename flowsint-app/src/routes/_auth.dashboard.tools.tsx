import { createFileRoute } from '@tanstack/react-router'

import { ScalpelConsolePage } from '@/components/compliance/scalpel-console-page'

import { FusionPlatformShell } from '@/fusion'



export const Route = createFileRoute('/_auth/dashboard/tools')({

  component: ToolsFusionPage,

})



function ToolsFusionPage() {

  return (

    <FusionPlatformShell

      title="Консоль Scalpel"

      subtitle="Каталог OSINT-коллекторов и инструментов разведки"

      activeSection="tools"

    >

      <ScalpelConsolePage embedded />

    </FusionPlatformShell>

  )

}



export default ToolsFusionPage

