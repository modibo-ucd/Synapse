import { useCallback, useEffect } from 'react'

import { safeStorage } from '../lib/storage/safeStorage'
import { useSettingsStore } from '../stores/settings'
import type { ThemePreference } from '../types/ui'

const THEME_KEY = 'synapse.theme'
const LIGHT_THEME_COLOR = '#F0F2F5'
const DARK_THEME_COLOR = '#243341'

function prefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** Resolves a preference to an effective dark flag. Exported for tests. */
export function resolveDark(theme: ThemePreference): boolean {
  if (theme === 'dark') return true
  if (theme === 'light') return false
  return prefersDark()
}

function subscribeMediaQuery(mq: MediaQueryList, handler: () => void): () => void {
  if (typeof mq.addEventListener === 'function') {
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }
  mq.addListener(handler)
  return () => mq.removeListener(handler)
}

export function useTheme() {
  const theme = useSettingsStore((state) => state.theme)
  const setTheme = useSettingsStore((state) => state.setTheme)

  useEffect(() => {
    const apply = () => {
      const dark = resolveDark(theme)
      document.documentElement.classList.toggle('dark', dark)
      const meta = document.querySelector('meta[name="theme-color"]')
      meta?.setAttribute('content', dark ? DARK_THEME_COLOR : LIGHT_THEME_COLOR)
      // Plain string key so public/theme-init.js can read it before first paint.
      safeStorage.setItem(THEME_KEY, theme)
    }
    apply()
    if (theme !== 'system') {
      return undefined
    }
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    return subscribeMediaQuery(mq, apply)
  }, [theme])

  const isDark = resolveDark(theme)

  const toggle = useCallback(() => {
    setTheme(isDark ? 'light' : 'dark')
  }, [isDark, setTheme])

  return { theme, setTheme, toggle, isDark }
}
