import { useMemo } from 'react'

import { useHistoryStore } from '../stores/history'
import { useUiStore } from '../stores/ui'
import type { Turn } from '../types/ui'

/** The turn shown in the trace panel: the selected one, else the latest. */
export function useSelectedTurn(): Turn | null {
  const sessions = useHistoryStore((state) => state.sessions)
  const activeSessionId = useHistoryStore((state) => state.activeSessionId)
  const selectedTurnId = useUiStore((state) => state.selectedTurnId)

  return useMemo(() => {
    const session = sessions.find((candidate) => candidate.id === activeSessionId)
    if (!session || session.turns.length === 0) return null
    if (selectedTurnId) {
      return session.turns.find((turn) => turn.id === selectedTurnId) ?? null
    }
    return session.turns[session.turns.length - 1] ?? null
  }, [sessions, activeSessionId, selectedTurnId])
}
