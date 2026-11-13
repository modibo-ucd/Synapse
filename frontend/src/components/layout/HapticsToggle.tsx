import { Vibrate, VibrateOff } from 'lucide-react'

import { haptic } from '../../lib/haptics'
import { useSettingsStore } from '../../stores/settings'

/** Settings toggle (6.8) for haptic feedback; default on. */
export function HapticsToggle() {
  const haptics = useSettingsStore((state) => state.haptics)
  const setHaptics = useSettingsStore((state) => state.setHaptics)

  const handleClick = () => {
    setHaptics(!haptics)
    if (!haptics) haptic(true) // brief confirmation buzz when enabling
  }

  return (
    <button
      type="button"
      data-testid="haptics-toggle"
      aria-pressed={haptics}
      aria-label={haptics ? 'Disable haptic feedback' : 'Enable haptic feedback'}
      onClick={handleClick}
      className="flex h-11 w-11 items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-accent-soft hover:text-accent"
    >
      {haptics ? (
        <Vibrate className="h-5 w-5" aria-hidden="true" />
      ) : (
        <VibrateOff className="h-5 w-5" aria-hidden="true" />
      )}
    </button>
  )
}
