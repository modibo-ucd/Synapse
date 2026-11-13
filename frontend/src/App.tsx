import { Disclaimer } from './components/Disclaimer'
import { AppShell } from './components/layout/AppShell'

export default function App() {
  return (
    <AppShell
      left={
        <div className="p-4">
          <h2 className="text-sm font-semibold">History</h2>
          <p className="mt-1 text-xs text-ink-muted">Sessions will appear here.</p>
        </div>
      }
      main={
        <div className="mx-auto max-w-3xl">
          <h1 className="font-display text-2xl font-semibold text-ink">Synapse</h1>
          <p className="mt-1 text-ink-muted">
            Agentic pharmacology research assistant — each question is answered independently
            from the corpus.
          </p>
          <div className="card-float mt-6 p-6">
            <Disclaimer />
          </div>
        </div>
      }
      right={
        <div className="p-4">
          <h2 className="text-sm font-semibold">Agent trace</h2>
          <p className="mt-1 text-xs text-ink-muted">Pipeline stages will appear here.</p>
        </div>
      }
    />
  )
}
