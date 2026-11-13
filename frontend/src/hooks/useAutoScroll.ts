import { useEffect, useRef, type DependencyList, type RefObject } from 'react'

const STICK_THRESHOLD_PX = 80

/**
 * Keeps the feed scrolled to the bottom when content grows, but only when the
 * user was already near the bottom (never yanks the view while they read).
 */
export function useAutoScroll<T extends HTMLElement>(
  ref: RefObject<T | null>,
  deps: DependencyList,
): void {
  const stickRef = useRef(true)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const onScroll = () => {
      stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < STICK_THRESHOLD_PX
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [ref])

  useEffect(() => {
    if (stickRef.current && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
