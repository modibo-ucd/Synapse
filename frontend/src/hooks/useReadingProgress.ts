import { useEffect, useState, type RefObject } from 'react'

import { revealedFraction } from '../lib/reading'

export interface ReadingProgressState {
  /** 0..1 — how much of the card has been revealed by the scroller's bottom edge. */
  fraction: number
  /** True when the card is taller than the scroller viewport (the bar is meaningful). */
  active: boolean
}

/**
 * rAF-throttled reading progress for a card inside a scroll container.
 * Recomputes on passive scroll and on size changes (ResizeObserver) and only
 * reports `active` when the card is taller than the scroller viewport.
 */
export function useReadingProgress(
  cardRef: RefObject<HTMLElement | null>,
  scrollerRef: RefObject<HTMLElement | null>,
): ReadingProgressState {
  const [state, setState] = useState<ReadingProgressState>({ fraction: 0, active: false })

  useEffect(() => {
    const card = cardRef.current
    const scroller = scrollerRef.current
    if (!card || !scroller) return

    let frame = 0

    const measure = () => {
      const cardRect = card.getBoundingClientRect()
      const scrollerRect = scroller.getBoundingClientRect()
      const fraction = revealedFraction(cardRect, scrollerRect)
      const active = cardRect.height > scrollerRect.height
      setState((prev) =>
        prev.fraction === fraction && prev.active === active ? prev : { fraction, active },
      )
    }

    const schedule = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(measure)
    }

    scroller.addEventListener('scroll', schedule, { passive: true })
    const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(schedule) : null
    observer?.observe(card)
    observer?.observe(scroller)
    measure()

    return () => {
      cancelAnimationFrame(frame)
      scroller.removeEventListener('scroll', schedule)
      observer?.disconnect()
    }
  }, [cardRef, scrollerRef])

  return state
}
