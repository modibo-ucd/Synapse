import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

import { safeStorage } from '../lib/storage/safeStorage'
import type { SettingsState, ThemePreference } from '../types/ui'

interface SettingsActions {
  setTheme: (theme: ThemePreference) => void
  setHaptics: (enabled: boolean) => void
  setHistoryOpen: (open: boolean) => void
  setTraceOpen: (open: boolean) => void
}

const initialState: SettingsState = {
  theme: 'system',
  haptics: true,
  historyOpen: true,
  traceOpen: true,
}

export const useSettingsStore = create<SettingsState & SettingsActions>()(
  persist(
    (set) => ({
      ...initialState,
      setTheme: (theme) => set({ theme }),
      setHaptics: (haptics) => set({ haptics }),
      setHistoryOpen: (historyOpen) => set({ historyOpen }),
      setTraceOpen: (traceOpen) => set({ traceOpen }),
    }),
    {
      name: 'synapse.settings',
      version: 1,
      storage: createJSONStorage(() => safeStorage),
    },
  ),
)
