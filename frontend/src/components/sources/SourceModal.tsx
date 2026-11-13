import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
} from 'react'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'

import { useMediaQuery } from '../../hooks/useMediaQuery'
import { useSourceDocument } from '../../hooks/useSourceDocument'
import type { HighlightRange } from '../../lib/markdown/rehypeSourceHighlight'
import { sourceTypeLabel } from '../../lib/sourceMeta'
import type { SourceViewTarget } from '../../types/ui'
import { SafeMarkdown } from '../SafeMarkdown'

interface SourceModalProps {
  target: SourceViewTarget | null
  onClose: () => void
}

/**
 * Native `<dialog>` reader for a source file, with the cited passages
 * cross-highlighted and prev/next passage navigation.
 */
export function SourceModal({ target, onClose }: SourceModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const bodyRef = useRef<HTMLDivElement>(null)
  const openerRef = useRef<HTMLElement | null>(null)
  const [passageIndex, setPassageIndex] = useState(0)
  const [primaryCount, setPrimaryCount] = useState(0)
  const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  const { status, document: sourceDoc, error, retry } = useSourceDocument(target?.fileName ?? null)

  const ranges = useMemo<HighlightRange[]>(() => {
    if (!sourceDoc || !target) return []
    const byId = new Map(sourceDoc.chunks.map((chunk) => [chunk.chunk_id, chunk]))
    const toRanges = (ids: string[], level: HighlightRange['level']): HighlightRange[] =>
      ids.flatMap((id) => {
        const span = byId.get(id)
        return span ? [{ start: span.start, end: span.end, level }] : []
      })
    return [
      ...toRanges(target.primaryChunkIds, 'primary'),
      ...toRanges(target.secondaryChunkIds, 'secondary'),
    ]
  }, [sourceDoc, target])

  // Open/close the native dialog and lock body scroll.
  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (target && !dialog.open) {
      openerRef.current = document.activeElement as HTMLElement | null
      setPassageIndex(0)
      dialog.showModal()
      document.body.style.overflow = 'hidden'
    } else if (!target && dialog.open) {
      dialog.close()
    }
  }, [target])

  // After the markdown renders, count and focus the current primary passage.
  useEffect(() => {
    if (status !== 'ready') return
    const body = bodyRef.current
    if (!body) return
    const passages = Array.from(body.querySelectorAll<HTMLElement>('[data-highlight="primary"]'))
    setPrimaryCount(passages.length)
    if (passages.length === 0) return
    const index = ((passageIndex % passages.length) + passages.length) % passages.length
    passages.forEach((passage) => passage.classList.remove('is-focused'))
    const current = passages[index]
    if (!current) return
    current.classList.add('is-focused')
    if (typeof current.scrollIntoView === 'function') {
      current.scrollIntoView({ block: 'center', behavior: reducedMotion ? 'auto' : 'smooth' })
    }
  }, [status, sourceDoc, passageIndex, reducedMotion])

  const closeDialog = useCallback(() => {
    dialogRef.current?.close()
  }, [])

  const handleDialogClose = useCallback(() => {
    document.body.style.overflow = ''
    openerRef.current?.focus()
    onClose()
  }, [onClose])

  const handleKeyDown = (event: KeyboardEvent<HTMLDialogElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      closeDialog()
    }
  }

  const handleBackdropClick = (event: MouseEvent<HTMLDialogElement>) => {
    if (event.target === event.currentTarget) closeDialog()
  }

  const goTo = (index: number) => {
    if (primaryCount <= 0) return
    setPassageIndex(((index % primaryCount) + primaryCount) % primaryCount)
  }

  return (
    <dialog
      ref={dialogRef}
      data-testid="source-modal"
      aria-label={sourceDoc ? `Source: ${sourceDoc.file_name}` : 'Source document'}
      onClose={handleDialogClose}
      onKeyDown={handleKeyDown}
      onClick={handleBackdropClick}
      className="source-modal"
    >
      <div className="glass-strong shadow-glass flex h-full flex-col overflow-hidden rounded-[inherit]">
        <header className="flex items-center gap-3 border-b border-line px-4 py-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="truncate font-mono text-sm font-medium text-ink">
                {sourceDoc?.file_name ?? target?.fileName}
              </span>
              {sourceDoc && (
                <span className="shrink-0 rounded bg-badge px-1.5 py-0.5 text-[11px] font-medium text-badge-ink">
                  {sourceTypeLabel(sourceDoc.source_type)}
                </span>
              )}
            </div>
            {sourceDoc && <p className="truncate text-xs text-ink-muted">{sourceDoc.title}</p>}
          </div>
          <div className="ml-auto flex items-center gap-1">
            <span
              data-testid="source-passage-count"
              className="px-1 text-xs tabular-nums text-ink-muted"
            >
              {primaryCount > 0 ? `${passageIndex + 1} / ${primaryCount}` : ''}
            </span>
            <button
              type="button"
              data-testid="source-prev"
              aria-label="Previous passage"
              disabled={primaryCount <= 1}
              onClick={() => goTo(passageIndex - 1)}
              className="flex h-9 w-9 items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-accent-soft hover:text-accent disabled:opacity-40"
            >
              <ChevronLeft className="h-5 w-5" aria-hidden="true" />
            </button>
            <button
              type="button"
              data-testid="source-next"
              aria-label="Next passage"
              disabled={primaryCount <= 1}
              onClick={() => goTo(passageIndex + 1)}
              className="flex h-9 w-9 items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-accent-soft hover:text-accent disabled:opacity-40"
            >
              <ChevronRight className="h-5 w-5" aria-hidden="true" />
            </button>
            <button
              type="button"
              data-testid="source-close"
              aria-label="Close source"
              onClick={closeDialog}
              className="flex h-9 w-9 items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-accent-soft hover:text-accent"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>
        </header>

        <div ref={bodyRef} className="sheet-pad min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {status === 'loading' && !sourceDoc && (
            <div data-testid="source-modal-loading" aria-busy="true" className="space-y-4">
              <div className="h-4 w-2/3 animate-pulse rounded bg-accent-soft" />
              <div className="h-4 w-full animate-pulse rounded bg-accent-soft" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-accent-soft" />
              <div className="h-4 w-1/2 animate-pulse rounded bg-accent-soft" />
            </div>
          )}
          {status === 'error' && !sourceDoc && (
            <div
              data-testid="source-modal-error"
              role="alert"
              className="flex flex-col items-start gap-3 py-8"
            >
              <p className="text-sm text-ink-muted">
                {error ?? 'Could not load the source document.'}
              </p>
              <button
                type="button"
                data-testid="source-modal-retry"
                onClick={retry}
                className="rounded-lg bg-action px-3 py-1.5 text-sm font-medium text-action-ink transition-colors hover:bg-action-hover"
              >
                Retry
              </button>
            </div>
          )}
          {sourceDoc && <SafeMarkdown highlightRanges={ranges}>{sourceDoc.markdown}</SafeMarkdown>}
        </div>
      </div>
    </dialog>
  )
}
