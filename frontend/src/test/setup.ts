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

// jsdom does not implement <dialog>.showModal()/close(), nor scrollIntoView.
if (typeof HTMLDialogElement !== 'undefined') {
  if (typeof HTMLDialogElement.prototype.showModal !== 'function') {
    HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
      this.setAttribute('open', '')
    }
  }
  if (typeof HTMLDialogElement.prototype.close !== 'function') {
    HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
      this.removeAttribute('open')
      this.dispatchEvent(new Event('close'))
    }
  }
}
if (typeof Element.prototype.scrollIntoView !== 'function') {
  Element.prototype.scrollIntoView = () => {}
}

// jsdom may lack requestAnimationFrame; polyfill so rAF-throttled hooks run
// under test (guarded so a native implementation is left untouched).
if (typeof window.requestAnimationFrame !== 'function') {
  window.requestAnimationFrame = (callback) => window.setTimeout(() => callback(Date.now()), 16)
  window.cancelAnimationFrame = (handle) => window.clearTimeout(handle)
}
