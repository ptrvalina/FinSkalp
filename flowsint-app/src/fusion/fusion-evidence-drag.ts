/** Drag payload for evidence → graph linking. */

export const FUSION_EVIDENCE_MIME = 'application/fusion-evidence'

export function setEvidenceDragData(e: React.DragEvent, contentHash: string) {
  e.dataTransfer.setData(FUSION_EVIDENCE_MIME, contentHash)
  e.dataTransfer.effectAllowed = 'link'
}

export function evidenceRowDragProps(contentHash: string) {
  return {
    draggable: true as const,
    onDragStart: (e: React.DragEvent) => setEvidenceDragData(e, contentHash),
  }
}
