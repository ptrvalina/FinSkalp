declare module 'react-syntax-highlighter' {
  import type { ComponentType } from 'react'
  export const Prism: ComponentType<Record<string, unknown>>
  const SyntaxHighlighter: ComponentType<Record<string, unknown>>
  export default SyntaxHighlighter
}

declare module 'react-syntax-highlighter/dist/esm/styles/prism' {
  export const oneDark: Record<string, unknown>
  export const oneLight: Record<string, unknown>
  export const dracula: Record<string, unknown>
}

declare module '@tiptap/react/menus' {
  export const BubbleMenu: import('react').ComponentType<Record<string, unknown>>
}

declare module '@tiptap/markdown' {
  export class MarkdownManager {
    constructor(options: { extensions: unknown[] })
    parse(text: string): unknown
  }
  export const Markdown: import('@tiptap/core').Extension
}
