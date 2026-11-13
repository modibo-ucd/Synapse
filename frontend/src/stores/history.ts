import { create } from 'zustand'
import { createJSONStorage, persist, type StateStorage } from 'zustand/middleware'

import { isQuotaExceeded, safeStorage } from '../lib/storage/safeStorage'
import { useUiStore } from './ui'
import type { AskResponse } from '../types/api'
import type { Session, Turn } from '../types/ui'

const STORAGE_KEY = 'synapse.history'
const MAX_SESSIONS = 50
const MAX_TURNS = 200
const MAX_TITLE_LENGTH = 48
const MAX_EXCERPT_LENGTH = 300

export function makeId(prefix: string): string {
  const random =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`
  return `${prefix}-${random}`
}

export function deriveTitle(question: string): string {
  const single = question.trim().replace(/\s+/g, ' ')
  if (single.length <= MAX_TITLE_LENGTH) {
    return single
  }
  return `${single.slice(0, MAX_TITLE_LENGTH - 1).trimEnd()}…`
}

function truncate(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1).trimEnd()}…` : value
}

/** Drops excerpt text beyond the first 8 chunks and trims large strings. */
export function compactForStorage(response: AskResponse): AskResponse {
  const retrieval = response.retrieval
  if (!retrieval || retrieval.chunks.length <= 8) {
    return response
  }
  return {
    ...response,
    retrieval: {
      ...retrieval,
      chunks: retrieval.chunks.map((chunk, index) =>
        index < 8
          ? { ...chunk, excerpt: truncate(chunk.excerpt, MAX_EXCERPT_LENGTH) }
          : { ...chunk, excerpt: '' },
      ),
    },
  }
}

/** Evicts the oldest turns (across the oldest sessions) down to `maxTurns`. */
function capTurns(sessions: Session[], maxTurns: number): Session[] {
  const total = sessions.reduce((sum, session) => sum + session.turns.length, 0)
  if (total <= maxTurns) {
    return sessions
  }
  let excess = total - maxTurns
  const result = sessions.map((session) => ({ ...session }))
  // Sessions are newest-first; iterate from the end (oldest) dropping oldest turns.
  for (let i = result.length - 1; i >= 0 && excess > 0; i -= 1) {
    const session = result[i]!
    const removed = Math.min(excess, session.turns.length)
    if (removed > 0) {
      session.turns = session.turns.slice(removed)
      excess -= removed
    }
  }
  return result
}

interface HistoryState {
  sessions: Session[]
  activeSessionId: string | null
  newSession: () => string
  selectSession: (id: string) => void
  renameSession: (id: string, title: string) => void
  deleteSession: (id: string) => void
  clearAll: () => void
  addTurn: (sessionId: string, question: string) => Turn
  updateTurn: (sessionId: string, turnId: string, patch: Partial<Turn>) => void
}

// Quota handling is wired into the persist storage adapter. The callbacks are
// assigned after the store exists so the fallback can evict via setState.
let quotaRetried = false
let handleQuota: (() => void) | null = null
let handleStorageError: (() => void) | null = null

const historyStorage: StateStorage = {
  getItem: (name) => safeStorage.getItem(name),
  setItem: (name, value) => {
    try {
      safeStorage.setItem(name, value)
      quotaRetried = false
    } catch (error) {
      if (isQuotaExceeded(error)) {
        handleQuota?.()
      } else {
        handleStorageError?.()
      }
    }
  },
  removeItem: (name) => safeStorage.removeItem(name),
}

export const useHistoryStore = create<HistoryState>()(
  persist(
    (set, get) => ({
      sessions: [],
      activeSessionId: null,

      newSession: () => {
        const now = Date.now()
        const session: Session = {
          id: makeId('session'),
          title: 'New question',
          titleEdited: false,
          createdAt: now,
          updatedAt: now,
          turns: [],
        }
        set({
          sessions: [session, ...get().sessions].slice(0, MAX_SESSIONS),
          activeSessionId: session.id,
        })
        return session.id
      },

      selectSession: (id) => set({ activeSessionId: id }),

      renameSession: (id, title) => {
        const trimmed = title.trim().slice(0, MAX_TITLE_LENGTH)
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id === id
              ? { ...session, title: trimmed, titleEdited: true, updatedAt: Date.now() }
              : session,
          ),
        }))
      },

      deleteSession: (id) => {
        set((state) => {
          const sessions = state.sessions.filter((session) => session.id !== id)
          return {
            sessions,
            activeSessionId:
              state.activeSessionId === id ? (sessions[0]?.id ?? null) : state.activeSessionId,
          }
        })
      },

      clearAll: () => set({ sessions: [], activeSessionId: null }),

      addTurn: (sessionId, question) => {
        const turn: Turn = {
          id: makeId('turn'),
          question: question.trim(),
          createdAt: Date.now(),
          status: 'pending',
        }
        set((state) => ({
          sessions: capTurns(
            state.sessions.map((session) => {
              if (session.id !== sessionId) {
                return session
              }
              const isFirst = session.turns.length === 0
              return {
                ...session,
                title:
                  isFirst && !session.titleEdited ? deriveTitle(question) : session.title,
                turns: [...session.turns, turn],
                updatedAt: Date.now(),
              }
            }),
            MAX_TURNS,
          ),
        }))
        return turn
      },

      updateTurn: (sessionId, turnId, patch) => {
        set((state) => ({
          sessions: state.sessions.map((session) =>
            session.id !== sessionId
              ? session
              : {
                  ...session,
                  turns: session.turns.map((candidate) =>
                    candidate.id === turnId ? { ...candidate, ...patch } : candidate,
                  ),
                  updatedAt: Date.now(),
                },
          ),
        }))
      },
    }),
    {
      name: STORAGE_KEY,
      version: 1,
      storage: createJSONStorage(() => historyStorage),
      partialize: (state) => ({
        sessions: state.sessions,
        activeSessionId: state.activeSessionId,
      }),
      migrate: (persistedState) => persistedState as HistoryState,
    },
  ),
)

handleQuota = () => {
  const { sessions, activeSessionId } = useHistoryStore.getState()
  if (!quotaRetried && sessions.length > 1) {
    quotaRetried = true
    const dropCount = Math.max(1, Math.ceil(sessions.length / 2))
    const kept = sessions.slice(dropCount)
    const activeKept = kept.some((session) => session.id === activeSessionId)
    useHistoryStore.setState({
      sessions: kept,
      activeSessionId: activeKept ? activeSessionId : (kept[0]?.id ?? null),
    })
    return
  }
  quotaRetried = false
  useUiStore.setState({ storageWarning: true })
}

handleStorageError = () => {
  useUiStore.setState({ storageWarning: true })
}

