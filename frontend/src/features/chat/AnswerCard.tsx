import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

import { ComparisonMatrix } from '../../components/ComparisonMatrix'
import { Disclaimer } from '../../components/Disclaimer'
import { EgfrCalculator } from '../../components/EgfrCalculator'
import { ReviewNotes } from '../../components/ReviewNotes'
import { SourceBadges } from '../../components/SourceBadges'
import { SafeMarkdown } from '../../components/SafeMarkdown'
import { MEDICAL_DISCLAIMER } from '../../lib/disclaimer'
import { countWords, estimateReadingSeconds, formatReadingTime } from '../../lib/reading'
import { useUiStore } from '../../stores/ui'
import type { Citation, ReviewVerdict } from '../../types/api'
import type { Turn } from '../../types/ui'

function groundingLabel(verdict: ReviewVerdict): string {
  switch (verdict) {
    case 'pass':
      return 'Grounding check passed'
    case 'revise':
      return 'Review notes'
    case 'insufficient_evidence':
      return 'Insufficient evidence in sources'
  }
}

function groundingClass(verdict: ReviewVerdict): string {
  switch (verdict) {
    case 'pass':
      return 'border-sage/40 bg-sage/10 text-sage'
    case 'revise':
      return 'border-champagne bg-champagne/50 text-accent'
    default:
      return 'border-line bg-surface text-ink-muted'
  }
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      await navigator.clipboard?.writeText(text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      // Clipboard unavailable; the button becomes a no-op.
    }
  }
  return (
    <button
      type="button"
      data-testid="copy-button"
      aria-label="Copy answer"
      onClick={() => void handleCopy()}
      className="rounded-lg p-1.5 text-ink-muted transition-colors hover:bg-accent-soft hover:text-accent"
    >
      {copied ? (
        <Check className="h-4 w-4" aria-hidden="true" />
      ) : (
        <Copy className="h-4 w-4" aria-hidden="true" />
      )}
    </button>
  )
}

interface AnswerCardProps {
  turn: Turn
}

/** The assistant message for one turn: answer, widgets, review notes, disclaimer. */
export function AnswerCard({ turn }: AnswerCardProps) {
  const setSelectedTurnId = useUiStore((state) => state.setSelectedTurnId)
  const setSourceView = useUiStore((state) => state.setSourceView)

  const openCitation = (citation: Citation) => {
    setSourceView({
      fileName: citation.source_file,
      primaryChunkIds: [citation.chunk_id],
      secondaryChunkIds: [],
    })
  }

  if (turn.status === 'pending') {
    return (
      <div data-testid="answer-pending" role="status" className="card-float p-5">
        <div className="flex items-center gap-3 text-sm text-ink-muted">
          <span
            aria-hidden="true"
            className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent"
          />
          Working… researching and verifying the answer.
        </div>
      </div>
    )
  }

  if (turn.status === 'error') {
    return (
      <div data-testid="answer-error" role="alert" className="card-float p-5">
        <p className="text-sm font-semibold text-ink">Something went wrong</p>
        <p className="mt-1 text-sm text-ink-muted">{turn.error ?? 'Unknown error.'}</p>
      </div>
    )
  }

  const response = turn.response
  if (!response) return null

  const showReadingTime = countWords(response.answer) > 60

  return (
    <article
      data-testid="answer-card"
      onClick={() => setSelectedTurnId(turn.id)}
      className="card-float animate-fade-up p-5"
    >
      <header className="flex items-center gap-2">
        <span className="font-display text-base font-semibold text-ink">Synapse</span>
        <span
          data-testid="grounding-chip"
          className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${groundingClass(response.review.verdict)}`}
        >
          <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current" />
          {groundingLabel(response.review.verdict)}
        </span>
        <span className="ml-auto flex items-center gap-1">
          {showReadingTime && (
            <span data-testid="reading-time" className="text-xs text-ink-muted">
              {formatReadingTime(estimateReadingSeconds(response.answer))}
            </span>
          )}
          <CopyButton text={response.answer} />
        </span>
      </header>

      <div className="mt-3">
        <SafeMarkdown citations={response.citations} onOpenCitation={openCitation}>
          {response.answer}
        </SafeMarkdown>
      </div>

      {response.comparison && (
        <ComparisonMatrix comparison={response.comparison} citations={response.citations} />
      )}
      {response.widgets?.map((widget) => (
        <EgfrCalculator key={widget.type} widget={widget} citations={response.citations} />
      ))}

      <ReviewNotes review={response.review} />

      <SourceBadges
        sources={response.sources}
        citations={response.citations}
        retrievedChunks={response.retrieval?.chunks ?? []}
      />

      <div className="mt-4 border-t border-line pt-3">
        <Disclaimer text={response.disclaimer || MEDICAL_DISCLAIMER} />
      </div>
    </article>
  )
}
