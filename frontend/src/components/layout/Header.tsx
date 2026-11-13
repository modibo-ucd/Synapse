import { History, PanelRight } from 'lucide-react'

import { useHistoryStore } from '../../stores/history'
import { useUiStore } from '../../stores/ui'
import { ThemeToggle } from './ThemeToggle'
import { HapticsToggle } from './HapticsToggle'

export function Header() {
  const drawer = useUiStore((state) => state.drawer)
  const setDrawer = useUiStore((state) => state.setDrawer)
  const activeTitle = useHistoryStore(
    (state) => state.sessions.find((session) => session.id === state.activeSessionId)?.title,
  )

  return (
    <header className="glass sticky top-0 z-30 flex items-center gap-2 px-3 py-2">
      <button
        type="button"
        data-testid="history-toggle"
        aria-label="Toggle history"
        aria-expanded={drawer === 'history'}
        onClick={() => setDrawer(drawer === 'history' ? null : 'history')}
        className="flex h-11 w-11 items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-accent-soft hover:text-accent lg:hidden"
      >
        <History className="h-5 w-5" aria-hidden="true" />
      </button>

      <span className="font-display text-lg font-semibold text-ink">Synapse</span>
      <span className="hidden truncate text-sm text-ink-muted md:block">
        {activeTitle ?? 'Pharmacology research assistant'}
      </span>

      <div className="ml-auto flex items-center gap-1">
        <button
          type="button"
          data-testid="trace-toggle"
          aria-label="Toggle agent trace"
          aria-expanded={drawer === 'trace'}
          onClick={() => setDrawer(drawer === 'trace' ? null : 'trace')}
          className="flex h-11 w-11 items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-accent-soft hover:text-accent lg:hidden"
        >
          <PanelRight className="h-5 w-5" aria-hidden="true" />
        </button>
        <HapticsToggle />
        <ThemeToggle />
      </div>
    </header>
  )
}
