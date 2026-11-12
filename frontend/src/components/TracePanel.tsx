import { useState } from 'react'

import type { StageEvent } from '../types/api'

const STAGES = [
  { id: 'plan', label: 'Plan' },
  { id: 'retrieve', label: 'Retrieve' },
  { id: 'tools', label: 'Tools' },
  { id: 'review', label: 'Review' },
  { id: 'answer', label: 'Answer' },
] as const

type StageId = (typeof STAGES)[number]['id']
type StageState = 'pending' | 'running' | 'done' | 'skipped'

interface TracePanelProps {
  events: StageEvent[]
  loading: boolean
}

function stageState(stage: StageId, events: StageEvent[], loading: boolean): StageState {
  const event = events.find((candidate) => candidate.stage === stage)
  if (event) {
    return event.status === 'skipped' ? 'skipped' : 'done'
  }
  if (!loading) {
    return 'pending'
  }
  const last = events[events.length - 1]
  const lastIndex = last ? STAGES.findIndex((candidate) => candidate.id === last.stage) : -1
  const thisIndex = STAGES.findIndex((candidate) => candidate.id === stage)
  return thisIndex === lastIndex + 1 ? 'running' : 'pending'
}

function formatDuration(durationMs: number): string {
  if (durationMs <= 0) {
    return ''
  }
  return durationMs >= 1000 ? `${(durationMs / 1000).toFixed(1)}s` : `${Math.round(durationMs)}ms`
}

function StateDot({ state }: { state: StageState }) {
  if (state === 'done') {
    return <span aria-hidden="true" className="h-2 w-2 rounded-full bg-emerald-500" />
  }
  if (state === 'running') {
    return <span aria-hidden="true" className="h-2 w-2 animate-pulse rounded-full bg-brand-500" />
  }
  if (state === 'skipped') {
    return <span aria-hidden="true" className="h-2 w-2 rounded-full bg-slate-300" />
  }
  return <span aria-hidden="true" className="h-2 w-2 rounded-full bg-slate-200" />
}

function StageDetails({ stage, event }: { stage: StageId; event: StageEvent }) {
  const details = event.details
  if (stage === 'plan' && details.sub_goals && details.sub_goals.length > 0) {
    return (
      <ul className="mt-1 list-disc pl-5 text-xs text-slate-600">
        {details.sub_goals.map((subGoal) => (
          <li key={subGoal.id}>{subGoal.question}</li>
        ))}
      </ul>
    )
  }
  if (stage === 'retrieve') {
    return (
      <div className="mt-1 text-xs text-slate-600">
        {details.chunk_count !== undefined && (
          <p>
            {details.chunk_count} chunk(s) · {details.mode}
          </p>
        )}
        {details.source_files && details.source_files.length > 0 && (
          <p className="mt-1">Files: {details.source_files.join(', ')}</p>
        )}
        {details.chunks && details.chunks.length > 0 && (
          <ul className="mt-1 list-disc pl-5">
            {details.chunks.map((chunk, index) => (
              <li key={`${chunk.source_file}-${index}`}>
                {chunk.source_file} — {chunk.section} (dense {chunk.dense_rank ?? '–'}, bm25{' '}
                {chunk.bm25_rank ?? '–'})
              </li>
            ))}
          </ul>
        )}
      </div>
    )
  }
  if (stage === 'tools' && details.tool_calls) {
    if (details.tool_calls.length === 0) {
      return <p className="mt-1 text-xs text-slate-500">No tools called.</p>
    }
    return (
      <ul className="mt-1 space-y-1 text-xs text-slate-600">
        {details.tool_calls.map((call, index) => (
          <li key={`${call.tool}-${index}`}>
            <span className="font-medium">{call.tool}</span> · {call.status} ·{' '}
            {JSON.stringify(call.arguments)}
          </li>
        ))}
      </ul>
    )
  }
  if (stage === 'review') {
    return (
      <div className="mt-1 text-xs text-slate-600">
        <p>Verdict: {details.verdict ?? '–'}</p>
        {details.unsupported_claims && details.unsupported_claims.length > 0 && (
          <ul className="mt-1 list-disc pl-5">
            {details.unsupported_claims.map((claim, index) => (
              <li key={`u-${index}`}>Unsupported: {claim}</li>
            ))}
          </ul>
        )}
        {details.ambiguity_flags && details.ambiguity_flags.length > 0 && (
          <ul className="mt-1 list-disc pl-5">
            {details.ambiguity_flags.map((flag, index) => (
              <li key={`a-${index}`}>Ambiguous: {flag}</li>
            ))}
          </ul>
        )}
      </div>
    )
  }
  if (stage === 'answer' && details.sources && details.sources.length > 0) {
    return <p className="mt-1 text-xs text-slate-600">Sources: {details.sources.join(', ')}</p>
  }
  return null
}

function TraceStage({
  stage,
  state,
  event,
}: {
  stage: StageId
  state: StageState
  event?: StageEvent
}) {
  const hasDetails = Boolean(event && Object.keys(event.details).length > 0)
  const summary = event?.summary ?? ''
  const label = STAGES.find((candidate) => candidate.id === stage)?.label

  return (
    <li className="rounded-md border border-slate-100 px-2 py-1.5">
      <details className="group" open={state === 'running'}>
        <summary className="flex cursor-pointer list-none items-center gap-2 text-sm">
          <StateDot state={state} />
          <span className="font-medium text-slate-700">{label}</span>
          {event && (
            <span className="ml-auto text-xs tabular-nums text-slate-400">
              {formatDuration(event.duration_ms)}
            </span>
          )}
          {hasDetails && (
            <span aria-hidden="true" className="text-xs text-slate-400 group-open:hidden">
              ▸
            </span>
          )}
        </summary>
        {summary && <p className="mt-1 pl-4 text-xs text-slate-500">{summary}</p>}
        {event && <StageDetails stage={stage} event={event} />}
      </details>
    </li>
  )
}

export function TracePanel({ events, loading }: TracePanelProps) {
  const [open, setOpen] = useState(true)

  return (
    <aside
      data-testid="trace-panel"
      aria-label="Agent trace"
      className="rounded-lg border border-slate-200 bg-white shadow-sm"
    >
      <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
        <h2 className="text-sm font-semibold text-slate-700">Agent trace</h2>
        <button
          type="button"
          data-testid="trace-toggle"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
          className="rounded-md px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 focus:outline-none focus:ring-2 focus:ring-brand-500/40"
        >
          {open ? 'Hide' : 'Show'}
        </button>
      </div>
      {open && (
        <ol className="motion-safe:animate-[trace-in_0.3s_ease-out] space-y-1 p-3">
          {STAGES.map((stage) => (
            <TraceStage
              key={stage.id}
              stage={stage.id}
              state={stageState(stage.id, events, loading)}
              event={events.find((candidate) => candidate.stage === stage.id)}
            />
          ))}
        </ol>
      )}
    </aside>
  )
}
