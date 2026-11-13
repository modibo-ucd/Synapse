import { afterEach, describe, expect, it, vi } from 'vitest'

import { isQuotaExceeded, safeStorage } from './safeStorage'

describe('safeStorage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
  })

  it('round-trips through localStorage when available', () => {
    safeStorage.setItem('key', 'value')
    expect(safeStorage.getItem('key')).toBe('value')
    safeStorage.removeItem('key')
    expect(safeStorage.getItem('key')).toBeNull()
  })

  it('falls back to an in-memory map when localStorage throws (private mode)', () => {
    const error = new DOMException('denied', 'SecurityError')
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw error
    })
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw error
    })
    safeStorage.setItem('key', 'value')
    expect(safeStorage.getItem('key')).toBe('value')
    safeStorage.removeItem('key')
    expect(safeStorage.getItem('key')).toBeNull()
  })

  it('propagates quota errors so the caller can evict and retry', () => {
    const quota = new DOMException('quota', 'QuotaExceededError')
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw quota
    })
    expect(() => safeStorage.setItem('key', 'value')).toThrow()
  })

  it('recognizes quota errors by name and legacy code', () => {
    expect(isQuotaExceeded({ name: 'QuotaExceededError' })).toBe(true)
    expect(isQuotaExceeded({ code: 22 })).toBe(true)
    expect(isQuotaExceeded({ code: 1014 })).toBe(true)
    expect(isQuotaExceeded(new Error('nope'))).toBe(false)
    expect(isQuotaExceeded(null)).toBe(false)
  })
})
