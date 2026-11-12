import type { Review } from '../types/api'

interface ReviewFlagsProps {
  review: Review
}

export function ReviewFlags({ review }: ReviewFlagsProps) {
  const hasFlags = review.unsupported_claims.length > 0 || review.ambiguity_flags.length > 0
  if (!hasFlags) {
    return null
  }

  return (
    <div
      data-testid="review-flags"
      role="alert"
      className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3"
    >
      <h3 className="text-sm font-semibold text-amber-800">Review notes</h3>
      <ul className="mt-1 list-disc pl-5 text-sm text-amber-800">
        {review.unsupported_claims.map((claim, index) => (
          <li key={`unsupported-${index}`}>Unsupported: {claim}</li>
        ))}
        {review.ambiguity_flags.map((flag, index) => (
          <li key={`ambiguity-${index}`}>Ambiguous: {flag}</li>
        ))}
      </ul>
    </div>
  )
}
