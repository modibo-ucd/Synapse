// localStorage wrapper: try/catch + in-memory fallback for private mode.
// Quota errors are re-thrown so the history store can evict and retry once.

const memory = new Map<string, string>()

function getLocalStorage(): Storage | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

export function isQuotaExceeded(error: unknown): boolean {
  if (typeof error !== 'object' || error === null) {
    return false
  }
  const candidate = error as { name?: string; code?: number }
  return (
    candidate.name === 'QuotaExceededError' ||
    candidate.code === 22 || // Firefox
    candidate.code === 1014 // legacy WebKit
  )
}

export const safeStorage = {
  getItem(key: string): string | null {
    try {
      const storage = getLocalStorage()
      return storage ? storage.getItem(key) : (memory.get(key) ?? null)
    } catch {
      return memory.get(key) ?? null
    }
  },

  setItem(key: string, value: string): void {
    const storage = getLocalStorage()
    if (!storage) {
      memory.set(key, value)
      return
    }
    try {
      storage.setItem(key, value)
      memory.delete(key)
    } catch (error) {
      if (isQuotaExceeded(error)) {
        throw error
      }
      memory.set(key, value)
    }
  },

  removeItem(key: string): void {
    try {
      getLocalStorage()?.removeItem(key)
    } catch {
      // ignore; clear the in-memory copy regardless
    }
    memory.delete(key)
  },
}
