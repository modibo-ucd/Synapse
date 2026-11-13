import { Moon, Sun } from 'lucide-react'

import { useTheme } from '../../hooks/useTheme'
import { haptic } from '../../lib/haptics'
import { useSettingsStore } from '../../stores/settings'

export function ThemeToggle() {
  const { isDark, toggle } = useTheme()
  const haptics = useSettingsStore((state) => state.haptics)

  const handleClick = () => {
    haptic(haptics)
    toggle()
  }

  return (
    <button
      type="button"
      data-testid="theme-toggle"
      aria-pressed={isDark}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      onClick={handleClick}
      className="flex h-11 w-11 items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-accent-soft hover:text-accent"
    >
      <span aria-hidden="true">
        {isDark ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
      </span>
    </button>
  )
}
