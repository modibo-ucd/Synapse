import '@testing-library/jest-dom/vitest'

// jsdom does not implement window.matchMedia; provide a minimal stub so the
// theme/media-query hooks can run under test (always reports "no match").
if (typeof window.matchMedia !== 'function') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (query: string): MediaQueryList => {
      const listeners = new Set<() => void>()
      const mql = {
        matches: false,
        media: query,
        onchange: null,
        addListener: (listener: () => void) => {
          listeners.add(listener)
        },
        removeListener: (listener: () => void) => {
          listeners.delete(listener)
        },
        addEventListener: (_type: string, listener: () => void) => {
          listeners.add(listener)
        },
        removeEventListener: (_type: string, listener: () => void) => {
          listeners.delete(listener)
        },
        dispatchEvent: () => false,
      }
      return mql as unknown as MediaQueryList
    },
  })
}

