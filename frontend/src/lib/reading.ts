// Reading-time estimation and formatting, used by the answer card label and
// the reading progress bar.

const WORDS_PER_MINUTE = 200

/** Counts whitespace-separated words after stripping Markdown syntax. */
export function countWords(markdown: string): number {
  return markdown
    .replace(/[#>*_`|\-[\]()]/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean).length
}

/** ~200 wpm, rounded to the nearest 5 s, with a 5 s floor. */
export function estimateReadingSeconds(markdown: string): number {
  const words = countWords(markdown)
  return Math.max(5, Math.round(words / (WORDS_PER_MINUTE / 60) / 5) * 5)
}

export function formatReadingTime(seconds: number): string {
  return seconds < 60 ? `${seconds} sec read` : `${Math.max(1, Math.round(seconds / 60))} min read`
}

/**
 * Fraction (0..1) of the card revealed above the scroller's bottom edge. Both
 * rects are viewport-relative (from `getBoundingClientRect`); the scroller's
 * bottom edge is the fixed reference while the card's top scrolls past it.
 */
export function revealedFraction(card: DOMRect, scroller: DOMRect): number {
  if (card.height <= 0) return 0
  return Math.min(1, Math.max(0, (scroller.bottom - card.top) / card.height))
}
