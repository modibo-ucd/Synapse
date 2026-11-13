import type { ReviewInfo } from '../types/api'

interface ReviewNotesProps {
  review: ReviewInfo
}

/**
 * Champagne block listing the reviewer's flags in plain language. Decision 7:
 * the revise verdict is labeled "Review notes", never "verified".
 */
export function ReviewNotes({ review }: ReviewNotesProps) {
  const notes = [
    ...review.unsupported_claims.map((claim) => `Unsupported claim: ${claim}`),
    ...review.ambiguity_flags.map((flag) => `Ambiguous wording: ${flag}`),
  ]
  if (notes.length === 0) return null

  return (
    <div
      data-testid="review-notes"
      className="mt-4 rounded-xl border border-champagne bg-champagne/40 p-3"
    >
      <h3 className="text-sm font-semibold text-ink">Review notes</h3>
      <ul className="mt-1 list-disc pl-5 text-sm text-ink-muted">
        {notes.map((note, index) => (
          <li key={`${index}-${note.slice(0, 16)}`}>{note}</li>
        ))}
      </ul>
    </div>
  )
}
