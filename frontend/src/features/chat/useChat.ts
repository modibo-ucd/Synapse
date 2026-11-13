import { useCallback, useMemo, useRef, useState } from 'react'

import { ApiError, askQuestion } from '../../lib/api/client'
import { compactForStorage, useHistoryStore } from '../../stores/history'
import type { Turn } from '../../types/ui'

const EMPTY_TURNS: Turn[] = []

/**
 * Non-streaming chat controller bound to the history store. Every question is
 * answered independently; prior turns are never sent to the backend.
 */
export function useChat() {
  const sessions = useHistoryStore((state) => state.sessions)
  const activeSessionId = useHistoryStore((state) => state.activeSessionId)
  const abortRef = useRef<AbortController | null>(null)
  const [pending, setPending] = useState(false)

  const turns = useMemo(() => {
    const session = sessions.find((candidate) => candidate.id === activeSessionId)
    return session?.turns ?? EMPTY_TURNS
  }, [sessions, activeSessionId])

  const submit = useCallback(async (question: string) => {
    const trimmed = question.trim()
    if (!trimmed || abortRef.current) return

    const store = useHistoryStore.getState()
    let sessionId = store.activeSessionId
    if (!sessionId || !store.sessions.some((session) => session.id === sessionId)) {
      sessionId = store.newSession()
    }
    const turn = useHistoryStore.getState().addTurn(sessionId, trimmed)

    const controller = new AbortController()
    abortRef.current = controller
    setPending(true)
    try {
      const response = await askQuestion(trimmed, controller.signal)
      useHistoryStore.getState().updateTurn(sessionId, turn.id, {
        status: 'done',
        response: compactForStorage(response),
      })
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Something went wrong. Please try again.'
      useHistoryStore.getState().updateTurn(sessionId, turn.id, { status: 'error', error: message })
    } finally {
      abortRef.current = null
      setPending(false)
    }
  }, [])

  const stop = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return { turns, pending, submit, stop }
}
