import { create } from 'zustand'

import type { SourceViewTarget } from '../types/ui'

// Non-persisted UI state. `activeSessionId` is owned by the history store
// (persisted); `storageWarning` is surfaced here because the history store's
// quota fallback must not re-enter its own persist write path.
export interface UiStoreState {
  selectedTurnId: string | null
  sourceView: SourceViewTarget | null
  zenTurnId: string | null
  drawer: 'history' | 'trace' | null
  storageWarning: boolean
}

export interface UiActions {
  setSelectedTurnId: (id: string | null) => void
  setSourceView: (target: SourceViewTarget | null) => void
  setZenTurnId: (id: string | null) => void
  setDrawer: (drawer: 'history' | 'trace' | null) => void
  setStorageWarning: (warning: boolean) => void
}

const initialState: UiStoreState = {
  selectedTurnId: null,
  sourceView: null,
  zenTurnId: null,
  drawer: null,
  storageWarning: false,
}

export const useUiStore = create<UiStoreState & UiActions>()((set) => ({
  ...initialState,
  setSelectedTurnId: (selectedTurnId) => set({ selectedTurnId }),
  setSourceView: (sourceView) => set({ sourceView }),
  setZenTurnId: (zenTurnId) => set({ zenTurnId }),
  setDrawer: (drawer) => set({ drawer }),
  setStorageWarning: (storageWarning) => set({ storageWarning }),
}))
