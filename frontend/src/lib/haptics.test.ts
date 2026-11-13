import { afterEach, describe, expect, it, vi } from 'vitest'

import { haptic } from './haptics'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('haptic', () => {
  it('does nothing when disabled', () => {
    const vibrate = vi.fn()
    vi.stubGlobal('navigator', { vibrate })
    haptic(false)
    expect(vibrate).not.toHaveBeenCalled()
  })

  it('does nothing when the vibrate API is missing', () => {
    vi.stubGlobal('navigator', {})
    expect(() => haptic(true)).not.toThrow()
  })

  it('vibrates when enabled and supported', () => {
    const vibrate = vi.fn()
    vi.stubGlobal('navigator', { vibrate })
    haptic(true)
    expect(vibrate).toHaveBeenCalledWith(12)
  })

  it('is suppressed by reduced motion', () => {
    const vibrate = vi.fn()
    vi.stubGlobal('navigator', { vibrate })
    vi.stubGlobal('matchMedia', () => ({ matches: true }) as MediaQueryList)
    haptic(true)
    expect(vibrate).not.toHaveBeenCalled()
  })
})
