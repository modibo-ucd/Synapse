import { Footer } from './components/Footer'
import { HistorySidebar } from './components/HistorySidebar'
import { TracePanel } from './components/TracePanel'
import { AppShell } from './components/layout/AppShell'
import { ChatPage } from './features/chat/ChatPage'
import { useSelectedTurn } from './hooks/useSelectedTurn'

export default function App() {
  const selectedTurn = useSelectedTurn()

  return (
    <AppShell
      left={<HistorySidebar />}
      main={<ChatPage />}
      right={<TracePanel turn={selectedTurn} />}
      footer={<Footer />}
    />
  )
}
