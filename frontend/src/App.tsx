import { Footer } from './components/Footer'
import { HistorySidebar } from './components/HistorySidebar'
import { SourceModal } from './components/sources/SourceModal'
import { TracePanel } from './components/TracePanel'
import { AppShell } from './components/layout/AppShell'
import { ChatPage } from './features/chat/ChatPage'
import { useSelectedTurn } from './hooks/useSelectedTurn'
import { useUiStore } from './stores/ui'

export default function App() {
  const selectedTurn = useSelectedTurn()
  const sourceView = useUiStore((state) => state.sourceView)
  const setSourceView = useUiStore((state) => state.setSourceView)

  return (
    <>
      <AppShell
        left={<HistorySidebar />}
        main={<ChatPage />}
        right={<TracePanel turn={selectedTurn} />}
        footer={<Footer />}
      />
      <SourceModal target={sourceView} onClose={() => setSourceView(null)} />
    </>
  )
}
