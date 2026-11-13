import { useEffect, type ReactNode } from 'react'

import { useMediaQuery } from '../../hooks/useMediaQuery'
import { useVisualViewport } from '../../hooks/useVisualViewport'
import { useUiStore } from '../../stores/ui'
import { Drawer } from './Drawer'
import { Header } from './Header'

interface AppShellProps {
  left?: ReactNode
  main: ReactNode
  right?: ReactNode
}

/**
 * Three-column layout at `>= 1024px` (left 280px / fluid / right 360px); the
 * sidebars become native `<dialog>` drawers below `lg`.
 */
export function AppShell({ left, main, right }: AppShellProps) {
  useVisualViewport()
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const drawer = useUiStore((state) => state.drawer)
  const setDrawer = useUiStore((state) => state.setDrawer)

  useEffect(() => {
    if (isDesktop && drawer) {
      setDrawer(null)
    }
  }, [isDesktop, drawer, setDrawer])

  return (
    <div className="app-shell">
      <Header />
      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)_360px]">
        {left ? (
          <nav
            aria-label="History"
            className="hidden min-h-0 overflow-y-auto border-r border-line scope-dark bg-side text-ink lg:block"
          >
            {left}
          </nav>
        ) : null}
        <main className="min-h-0 overflow-y-auto p-4 lg:p-6">{main}</main>
        {right ? (
          <aside
            aria-label="Agent trace"
            className="hidden min-h-0 overflow-y-auto border-l border-line lg:block"
          >
            {right}
          </aside>
        ) : null}
      </div>
      <Drawer side="left" open={drawer === 'history'} onClose={() => setDrawer(null)} label="History">
        {left}
      </Drawer>
      <Drawer side="right" open={drawer === 'trace'} onClose={() => setDrawer(null)} label="Agent trace">
        {right}
      </Drawer>
    </div>
  )
}
