import { useEffect, useRef, useState } from 'react'

import { getHealth } from '../lib/api/client'

const BUILDING_INTERVAL_MS = 5_000
const STEADY_INTERVAL_MS = 30_000
const FAILURE_INTERVAL_MS = 10_000

export interface HealthSnapshot {
  status: 'ok' | 'unreachable'
  index: 'building' | 'ready' | 'degraded'
  llm_configured: boolean
  version?: string
  indexStats?: { files: number; chunks: number; embedding_model: string | null } | null
}

const UNREACHABLE: HealthSnapshot = {
  status: 'unreachable',
  index: 'ready',
  llm_configured: false,
  indexStats: null,
}

/**
 * Polls `/health`: 5 s while the index builds, 30 s once ready, and a short
 * retry window on failure. Pauses while the tab is hidden and aborts on unmount.
 */
export function useHealth(): HealthSnapshot | null {
  const [snapshot, setSnapshot] = useState<HealthSnapshot | null>(null)
  const reachableRef = useRef(false)
  const indexRef = useRef<'building' | 'ready' | 'degraded'>('building')

  useEffect(() => {
    let disposed = false
    let controller: AbortController | null = null
    let timer: number | undefined

    const clearTimer = () => {
      if (timer !== undefined) {
        window.clearTimeout(timer)
        timer = undefined
      }
    }

    const intervalMs = () => {
      if (!reachableRef.current) return FAILURE_INTERVAL_MS
      return indexRef.current === 'building' ? BUILDING_INTERVAL_MS : STEADY_INTERVAL_MS
    }

    const schedule = () => {
      if (disposed) return
      clearTimer()
      timer = window.setTimeout(() => {
        void poll()
      }, intervalMs())
    }

    const poll = async () => {
      if (disposed) return
      if (document.hidden) {
        schedule()
        return
      }
      controller = new AbortController()
      try {
        const health = await getHealth(controller.signal)
        if (disposed) return
        reachableRef.current = true
        indexRef.current = health.index
        setSnapshot({
          status: 'ok',
          index: health.index,
          llm_configured: health.llm_configured,
          version: health.version,
          indexStats: health.index_stats ?? null,
        })
      } catch {
        if (disposed) return
        reachableRef.current = false
        setSnapshot((previous) => (previous ? { ...previous, status: 'unreachable' } : UNREACHABLE))
      } finally {
        schedule()
      }
    }

    void poll()

    return () => {
      disposed = true
      clearTimer()
      controller?.abort()
    }
  }, [])

  return snapshot
}
