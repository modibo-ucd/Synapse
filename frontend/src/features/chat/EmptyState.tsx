import { Sparkles } from 'lucide-react'

import { Disclaimer } from '../../components/Disclaimer'
import { EXAMPLE_QUESTIONS } from '../../lib/examples'

const INDEPENDENCE_HINT = 'Each question is answered independently from the corpus.'

interface EmptyStateProps {
  onSelect: (question: string) => void
}

/** First-visit state: brand mark, purpose, independence hint and the 4 public questions. */
export function EmptyState({ onSelect }: EmptyStateProps) {
  return (
    <div data-testid="empty-state" className="mx-auto max-w-2xl py-6 text-center">
      <span
        aria-hidden="true"
        className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent"
      >
        <Sparkles className="h-6 w-6" />
      </span>
      <h1 className="mt-4 font-display text-2xl font-semibold text-ink">Synapse</h1>
      <p className="mt-1 text-ink-muted">Agentic pharmacology research assistant.</p>
      <p data-testid="independence-hint" className="mt-2 text-sm text-ink-muted">
        {INDEPENDENCE_HINT}
      </p>

      <div className="mt-6 grid gap-3 text-left sm:grid-cols-2">
        {EXAMPLE_QUESTIONS.map((example) => (
          <button
            key={example.id}
            type="button"
            data-testid={`example-${example.id}`}
            onClick={() => onSelect(example.text)}
            className="rounded-xl border border-line bg-surface p-3 text-left text-sm text-ink transition-colors hover:bg-accent-soft"
          >
            {example.text}
          </button>
        ))}
      </div>

      <div className="mt-8 text-left">
        <Disclaimer />
      </div>
    </div>
  )
}
