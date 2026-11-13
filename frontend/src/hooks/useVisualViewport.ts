import { useEffect } from 'react'

/** Keeps `--app-height` in sync with the visual viewport (iOS keyboard). */
export function useVisualViewport(): void {
  useEffect(() => {
    const vv = window.visualViewport
    if (!vv) return
    const root = document.documentElement
    const apply = (): void => {
      root.style.setProperty('--app-height', `${vv.height}px`)
      root.dataset.vv = '1'
      if (vv.offsetTop > 0) window.scrollTo(0, 0) // iOS shifts the layout viewport when the keyboard opens
    }
    apply()
    vv.addEventListener('resize', apply)
    vv.addEventListener('scroll', apply)
    return () => {
      vv.removeEventListener('resize', apply)
      vv.removeEventListener('scroll', apply)
      root.style.removeProperty('--app-height')
      delete root.dataset.vv
    }
  }, [])
}
