// Haptics: feature-detected, reduced-motion aware, opt-out via settings.

export function haptic(enabled: boolean, ms = 12): void {
  if (!enabled || typeof navigator === 'undefined' || !('vibrate' in navigator)) return
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
  navigator.vibrate(ms) // must run inside a user-gesture handler
}
