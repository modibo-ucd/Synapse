import { useState } from 'react'
import { Check, Loader2, X } from 'lucide-react'

import type { StageName, StageTrace } from '../types/api'
import type { Turn } from '../types/ui'

const STAGE_ORDER: StageName[] = ['plan', 'retrieve', 'tools', 'review', 'answer']

const STAGE_LABELS: Record<StageName, string> = {
  plan: 'Analyzing your question',
  retrieve: 'Searching sources (semantic + keyword)',
  tools: 'Consulting local tools',
  review: 'Checking claims against sources',
  answer: 'Composing cited answer',
}

// Collapse preference is remembered per turn for the SPA session (not persisted).
const collapseByTurn = new Map<string, boolean>()

function mergeStages(live: StageTrace[], trace: StageTrace[] | null | undefined): StageTrace[] {
  const byStage = new Map<StageName, StageTrace>()
  for (const stage of trace ?? []) byStage.set(stage.stage, stage)
  for (const stage of live) byStage.set(stage.stage, stage)
  return STAGE_ORDER.map(
    (name): StageTrace =>
      byStage.get(name) ?? { stage: name, status: 'pending', duration_ms: null, summary: null },
  )
}

function formatLatency(latencyMs: number | undefined): string {
  const ms = latencyMs ?? 0
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`
}

function StageRow({ stage }: { stage: StageTrace }) {
  const label = STAGE_LABELS[stage.stage]
  const pending = stage.status === 'pending'
  return (
    <li className={`flex items-center gap-2 text-sm ${pending ? 'text-ink-muted' : 'text-ink'}`}>
      <span aria-hidden="true" className="flex h-4 w-4 items-center justify-center">
        {stage.status === 'done' && <Check className="h-4 w-4 text-sage" />}
        {stage.status === 'running' && <Loader2 className="h-4 w-4 animate-spin text-accent" />}
        {stage.status === 'error' && <X className="h-4 w-4 text-champagne" />}
        {(stage.status === 'pending' || stage.status === 'skipped') && (
          <span className="h-1.5 w-1.5 rounded-full border border-line" />
        )}
      </span>
      <span>{label}</span>
      {stage.summary && (
        <span className="ml-auto truncate text-xs text-ink-muted">{stage.summary}</span>
      )}
    </li>
  )
}

interface StageTimelineProps {
  turn: Turn
}

/**
 * "Stream of Thought" timeline (6.5). Renders only real stage events: live
 * events while streaming, the completed trace when done. Without any events
 * (e.g. the non-streaming fallback) it shows an indeterminate state — never
 * simulated steps.
 */
export function StageTimeline({ turn }: StageTimelineProps) {
  const isLive = turn.status === 'pending' && (turn.liveStages?.length ?? 0) > 0
  const isDone = turn.status === 'done'

  const [expanded, setExpanded] = useState<boolean>(() => {
    const remembered = collapseByTurn.get(turn.id)
    return remembered ?? turn.status !== 'done'
  })

  const toggle = () => {
    setExpanded((prev) => {
      const next = !prev
      collapseByTurn.set(turn.id, next)
      return next
    })
  }

  if (turn.status === 'pending' && !isLive) {
    return (
      <div
        data-testid="stage-timeline"
        role="status"
        className="flex items-center gap-2 text-sm text-ink-muted"
      >
        <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden="true" />
        Working… researching and verifying the answer.
      </div>
    )
  }

  const stages = mergeStages(turn.liveStages ?? [], turn.response?.trace ?? [])
  const doneCount = stages.filter((stage) => stage.status === 'done').length

  if (isDone && !expanded) {
    return (
      <div data-testid="stage-timeline">
        <button
          type="button"
          aria-expanded={false}
          onClick={toggle}
          className="rounded text-xs text-ink-muted transition-colors hover:text-accent"
        >
          Answered in {formatLatency(turn.response?.latency_ms)} | {doneCount} stages |{' '}
          {turn.response?.sources.length ?? 0} sources
        </button>
      </div>
    )
  }

  return (
    <div
      data-testid="stage-timeline"
      aria-live="polite"
      className="rounded-lg border border-line bg-surface p-3"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
          Stream of thought
        </span>
        {isDone && (
          <button
            type="button"
            aria-expanded={true}
            onClick={toggle}
            className="text-xs text-ink-muted transition-colors hover:text-accent"
          >
            Collapse
          </button>
        )}
      </div>
      <ol className="mt-2 space-y-1.5">
        {stages.map((stage) => (
          <StageRow key={stage.stage} stage={stage} />
        ))}
      </ol>
    </div>
  )
}
