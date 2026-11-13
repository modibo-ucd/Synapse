import { useCallback, useMemo, useRef, useState } from 'react'

import { useAskStream } from '../../hooks/useAskStream'
import { compactForStorage, useHistoryStore } from '../../stores/history'
import type { StageTrace } from '../../types/api'
import type { Turn } from '../../types/ui'

const EMPTY_TURNS: Turn[] = []

/**
 * Chat controller bound to the history store. Streams stage events live via
 * `useAskStream` (with a silent fallback to `POST /ask`); every question is
 * answered independently and prior turns are never sent to the backend.
 */
export function useChat() {
  const sessions = useHistoryStore((state) => state.sessions)
  const activeSessionId = useHistoryStore((state) => state.activeSessionId)
  const runningRef = useRef(false)
  const [pending, setPending] = useState(false)
  const { start, stop: stopStream } = useAskStream()

  const turns = useMemo(() => {
    const session = sessions.find((candidate) => candidate.id === activeSessionId)
    return session?.turns ?? EMPTY_TURNS
  }, [sessions, activeSessionId])

  const submit = useCallback(
    async (question: string) => {
      const trimmed = question.trim()
      if (!trimmed || runningRef.current) return

      const store = useHistoryStore.getState()
      let sessionId = store.activeSessionId
      if (!sessionId || !store.sessions.some((session) => session.id === sessionId)) {
        sessionId = store.newSession()
      }
      const turn = useHistoryStore.getState().addTurn(sessionId, trimmed)

      const liveStages: StageTrace[] = []
      runningRef.current = true
      setPending(true)
      await start(trimmed, {
        onStage: (stage) => {
          liveStages.push(stage)
          useHistoryStore.getState().updateTurn(sessionId, turn.id, {
            liveStages: [...liveStages],
          })
        },
        onResult: (response) => {
          useHistoryStore.getState().updateTurn(sessionId, turn.id, {
            status: 'done',
            response: compactForStorage(response),
            liveStages: undefined,
          })
        },
        onError: (error) => {
          useHistoryStore.getState().updateTurn(sessionId, turn.id, {
            status: 'error',
            error: error.message,
            liveStages: undefined,
          })
        },
      })
      runningRef.current = false
      setPending(false)
    },
    [start],
  )

  const stop = useCallback(() => {
    stopStream()
  }, [stopStream])

  return { turns, pending, submit, stop }
}
