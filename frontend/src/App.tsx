import { Disclaimer } from './components/Disclaimer'
import { ChatPage } from './features/chat/ChatPage'

export default function App() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto w-full max-w-3xl px-4 py-4">
          <h1 className="text-xl font-semibold tracking-tight">Synapse</h1>
          <p className="text-sm text-slate-500">Agentic pharmacology research assistant</p>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
        <ChatPage />
      </main>
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto w-full max-w-3xl px-4 py-4">
          <Disclaimer />
        </div>
      </footer>
    </div>
  )
}
