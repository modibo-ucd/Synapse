import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'

import { Disclaimer } from './Disclaimer'
import { ReviewNotes } from './ReviewNotes'
import { SourceBadges } from './SourceBadges'
import { SafeMarkdown } from './SafeMarkdown'
import { MEDICAL_DISCLAIMER } from '../lib/disclaimer'
import { restoreZenFocus } from '../lib/zenFocus'
import { useUiStore } from '../stores/ui'
import type { Citation } from '../types/api'
import type { Turn } from '../types/ui'

interface ZenReaderProps {
  turn: Turn
  onClose: () => void
}

/**
 * Focus reading mode (6.4): a full-screen reader showing only one answer in a
 * `max-w-[68ch]` column. Esc or the "Exit focus" button closes and returns
 * focus to the zen toggle that opened it.
 */
export function ZenReader({ turn, onClose }: ZenReaderProps) {
  const exitRef = useRef<HTMLButtonElement>(null)
  const response = turn.response

  useEffect(() => {
    exitRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        restoreZenFocus()
        onClose()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  if (!response) return null

  const openCitation = (citation: Citation) => {
    useUiStore.getState().setSourceView({
      fileName: citation.source_file,
      primaryChunkIds: [citation.chunk_id],
      secondaryChunkIds: [],
    })
  }

  const close = () => {
    restoreZenFocus()
    onClose()
  }

  return (
    <div
      data-testid="zen-reader"
      role="dialog"
      aria-modal="true"
      aria-label="Focus reading mode"
      className="fixed inset-0 z-50 overflow-y-auto bg-app"
    >
      <button
        ref={exitRef}
        type="button"
        data-testid="zen-exit"
        onClick={close}
        className="fixed right-4 top-4 z-10 flex h-11 items-center gap-2 rounded-full border border-line bg-surface px-4 text-sm font-medium text-ink shadow-float hover:bg-accent-soft"
      >
        <X className="h-4 w-4" aria-hidden="true" />
        Exit focus
      </button>
      <article className="mx-auto max-w-[68ch] px-6 py-14">
        <p className="font-display text-2xl font-semibold text-ink">{turn.question}</p>
        <div className="mt-6 text-lg leading-8">
          <SafeMarkdown citations={response.citations} onOpenCitation={openCitation}>
            {response.answer}
          </SafeMarkdown>
        </div>
        <ReviewNotes review={response.review} />
        <div className="mt-6">
          <SourceBadges
            sources={response.sources}
            citations={response.citations}
            retrievedChunks={response.retrieval?.chunks ?? []}
          />
        </div>
        <div className="mt-6 border-t border-line pt-4">
          <Disclaimer text={response.disclaimer || MEDICAL_DISCLAIMER} />
        </div>
      </article>
    </div>
  )
}
