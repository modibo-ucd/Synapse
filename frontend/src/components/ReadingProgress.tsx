import type { RefObject } from 'react'

import { useReadingProgress } from '../hooks/useReadingProgress'

interface ReadingProgressProps {
  cardRef: RefObject<HTMLElement | null>
  scrollerRef: RefObject<HTMLElement | null>
}

/**
 * 2px sticky progress bar (6.2), shown only when the card is taller than the
 * scroller viewport. Width is driven by `transform: scaleX` for GPU-only
 * updates; the track uses `--c-line` and the fill `--c-accent` (ocean/glacial).
 */
export function ReadingProgress({ cardRef, scrollerRef }: ReadingProgressProps) {
  const { fraction, active } = useReadingProgress(cardRef, scrollerRef)
  if (!active) return null

  return (
    <div data-testid="reading-progress" aria-hidden="true" className="sticky top-0 z-10 -mx-5 h-0.5 bg-line">
      <div className="h-full origin-left bg-accent" style={{ transform: `scaleX(${fraction})` }} />
    </div>
  )
}