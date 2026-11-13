import { useCallback, useEffect, useState } from 'react'

import { ApiError, getSourceDocument } from '../lib/api/client'
import type { SourceDocument } from '../types/api'

const cache = new Map<string, SourceDocument>()
const etags = new Map<string, string>()

export type SourceDocumentStatus = 'loading' | 'ready' | 'error'

export interface SourceDocumentState {
  status: SourceDocumentStatus
  document: SourceDocument | null
  error: string | null
  retry: () => void
}

/** Test-only helper: clears the module-level document cache. */
export function clearSourceDocumentCache(): void {
  cache.clear()
  etags.clear()
}

/**
 * Loads a source document by file name, caching it keyed by file name + ETag.
 * Revalidates with `If-None-Match`; a 304 reuses the cached copy, and a
 * network error keeps showing a stale document when one exists.
 */
export function useSourceDocument(fileName: string | null): SourceDocumentState {
  const [nonce, setNonce] = useState(0)
  const [state, setState] = useState<Omit<SourceDocumentState, 'retry'>>(() => {
    const cached = fileName ? cache.get(fileName) : null
    return { status: cached ? 'ready' : 'loading', document: cached ?? null, error: null }
  })

  useEffect(() => {
    if (!fileName) {
      setState({ status: 'loading', document: null, error: null })
      return
    }
    let disposed = false
    const controller = new AbortController()
    const cached = cache.get(fileName)
    setState({ status: cached ? 'ready' : 'loading', document: cached ?? null, error: null })

    void (async () => {
      try {
        const result = await getSourceDocument(fileName, etags.get(fileName), controller.signal)
        if (disposed) return
        if (result.document) {
          cache.set(fileName, result.document)
          if (result.etag) etags.set(fileName, result.etag)
          setState({ status: 'ready', document: result.document, error: null })
        } else {
          setState({ status: 'ready', document: cache.get(fileName) ?? null, error: null })
        }
      } catch (error) {
        if (disposed) return
        const message =
          error instanceof ApiError ? error.message : 'Could not load the source document.'
        const stale = cache.get(fileName)
        setState({
          status: stale ? 'ready' : 'error',
          document: stale ?? null,
          error: stale ? null : message,
        })
      }
    })()

    return () => {
      disposed = true
      controller.abort()
    }
  }, [fileName, nonce])

  const retry = useCallback(() => setNonce((value) => value + 1), [])

  return { ...state, retry }
}
