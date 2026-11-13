// UI-only types. camelCase is intentional; these never cross the wire.

import type { AskResponse, StageTrace } from './api'

export type TurnStatus = 'pending' | 'done' | 'error'

export interface Turn {
  id: string
  question: string
  createdAt: number
  status: TurnStatus
  response?: AskResponse // compacted before persisting
  error?: string
  liveStages?: StageTrace[] // NOT persisted
}

export interface Session {
  id: string
  title: string
  titleEdited: boolean
  createdAt: number
  updatedAt: number
  turns: Turn[]
}

export type ThemePreference = 'light' | 'dark' | 'system'

export interface SettingsState {
  theme: ThemePreference
  haptics: boolean
  historyOpen: boolean
  traceOpen: boolean
}

export interface SourceViewTarget {
  fileName: string
  primaryChunkIds: string[] // cited chunks (strong highlight)
  secondaryChunkIds: string[] // other retrieved chunks from this file (soft highlight)
}

export interface UiState {
  activeSessionId: string | null
  selectedTurnId: string | null
  sourceView: SourceViewTarget | null
  zenTurnId: string | null
  drawer: 'history' | 'trace' | null
}
