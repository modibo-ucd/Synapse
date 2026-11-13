import { Lock } from 'lucide-react'

import { useHealth } from '../hooks/useHealth'
import { APP_VERSION } from '../lib/version'

function footerDot(health: ReturnType<typeof useHealth>): { dot: string; text: string } {
  if (!health) return { dot: 'bg-ink-muted', text: 'Checking…' }
  if (health.status === 'unreachable') return { dot: 'bg-ink-muted', text: 'API unreachable' }
  if (health.index === 'building') return { dot: 'bg-glacial animate-dot-pulse', text: 'Indexing…' }
  if (health.index === 'degraded') {
    return { dot: 'bg-transparent ring-1 ring-inset ring-champagne', text: 'BM25-only' }
  }
  return { dot: 'bg-sage', text: 'Index ready' }
}

/** One-line footer (6.9): status dot, version badge to /docs, privacy note. */
export function Footer() {
  const health = useHealth()
  const status = footerDot(health)
  const version = health?.version ?? APP_VERSION

  return (
    <div
      data-testid="footer"
      className="mx-auto flex max-w-6xl items-center gap-2 px-2 text-xs text-ink-muted"
    >
      <span aria-hidden="true" className={`h-2 w-2 rounded-full ${status.dot}`} />
      <span data-testid="footer-status">{status.text}</span>
      <a
        data-testid="footer-version"
        href="/docs"
        target="_blank"
        rel="noopener noreferrer"
        className="rounded bg-badge px-1.5 py-0.5 text-[11px] font-medium text-badge-ink"
      >
        v{version}
      </a>
      <span
        data-testid="footer-history-note"
        title="Questions are sent to the configured LLM endpoint; history stays in this browser."
        className="ml-auto flex items-center gap-1"
      >
        <Lock className="h-3 w-3" aria-hidden="true" />
        History stays in this browser
      </span>
    </div>
  )
}
