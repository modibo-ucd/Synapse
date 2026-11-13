import { Footer } from './components/Footer'
import { HistorySidebar } from './components/HistorySidebar'
import { SourceModal } from './components/sources/SourceModal'
import { TracePanel } from './components/TracePanel'
import { ZenReader } from './components/ZenReader'
import { AppShell } from './components/layout/AppShell'
import { ChatPage } from './features/chat/ChatPage'
import { useSelectedTurn } from './hooks/useSelectedTurn'
import { useHistoryStore } from './stores/history'
import { useUiStore } from './stores/ui'

export default function App() {
  const selectedTurn = useSelectedTurn()
  const sourceView = useUiStore((state) => state.sourceView)
  const setSourceView = useUiStore((state) => state.setSourceView)
  const zenTurnId = useUiStore((state) => state.zenTurnId)
  const setZenTurnId = useUiStore((state) => state.setZenTurnId)
  const zenTurn = useHistoryStore((state) => {
    if (!zenTurnId) return null
    for (const session of state.sessions) {
      const turn = session.turns.find((candidate) => candidate.id === zenTurnId)
      if (turn) return turn
    }
    return null
  })

  return (
    <>
      <AppShell
        left={<HistorySidebar />}
        main={<ChatPage />}
        right={<TracePanel turn={selectedTurn} />}
        footer={<Footer />}
      />
      <SourceModal target={sourceView} onClose={() => setSourceView(null)} />
      {zenTurn && <ZenReader turn={zenTurn} onClose={() => setZenTurnId(null)} />}
    </>
  )
}
