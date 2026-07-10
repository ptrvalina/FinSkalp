import '@tiptap/core'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    highlight: {
      toggleHighlight: () => ReturnType
    }
    taskList: {
      toggleTaskList: () => ReturnType
    }
  }

  interface ExtensionManager {
    baseExtensions?: unknown[]
  }
}
