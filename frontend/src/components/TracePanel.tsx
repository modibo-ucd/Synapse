import { useHealth, type HealthSnapshot } from '../hooks/useHealth'
import type { RetrievedChunk, ReviewInfo, StageTrace, ToolCallInfo, Usage } from '../types/api'
import type { Turn } from '../types/ui'

function formatDuration(durationMs: number | null): string {
  if (durationMs === null || durationMs <= 0) return '–'
  return durationMs >= 1000 ? `${(durationMs / 1000).toFixed(1)}s` : `${Math.round(durationMs)}ms`
}

function indexStatus(health: HealthSnapshot | null): { dot: string; text: string; extra?: string } {
  if (!health) {
    return { dot: 'bg-ink-muted', text: 'Checking index…' }
  }
  if (health.status === 'unreachable') {
    return { dot: 'bg-ink-muted', text: 'API unreachable' }
  }
  const stats = health.indexStats
  const extra =
    stats && stats.chunks > 0
      ? `${stats.files} files · ${stats.chunks} chunks${stats.embedding_model ? ` · ${stats.embedding_model}` : ''}`
      : undefined
  if (health.index === 'building') {
    return { dot: 'bg-glacial animate-dot-pulse', text: 'Indexing…', extra }
  }
  if (health.index === 'degraded') {
    return { dot: 'bg-transparent ring-1 ring-inset ring-champagne', text: 'BM25-only', extra }
  }
  return { dot: 'bg-sage', text: 'Index ready', extra }
}

function IndexStatus({ health }: { health: HealthSnapshot | null }) {
  const status = indexStatus(health)
  return (
    <section data-testid="trace-index-status" aria-label="Index status">
      <div className="flex items-center gap-2 text-sm text-ink">
        <span aria-hidden="true" className={`h-2 w-2 rounded-full ${status.dot}`} />
        <span>{status.text}</span>
      </div>
      {status.extra && <p className="mt-1 text-xs text-ink-muted">{status.extra}</p>}
    </section>
  )
}

function QueryMetrics({
  trace,
  latencyMs,
  usage,
}: {
  trace: StageTrace[]
  latencyMs: number
  usage: Usage
}) {
  const durations = trace.filter((stage) => stage.duration_ms && stage.duration_ms > 0)
  const max = Math.max(1, ...durations.map((stage) => stage.duration_ms ?? 0))
  const { tokens_in: tokensIn, tokens_out: tokensOut } = usage

  return (
    <section data-testid="trace-metrics" aria-label="Query metrics" className="rounded-lg border border-line p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Latest query</p>
      <p className="mt-1 text-sm text-ink">
        {latencyMs >= 1000 ? `${(latencyMs / 1000).toFixed(1)}s` : `${Math.round(latencyMs)}ms`} total ·{' '}
        {tokensIn} in · {tokensOut} out tokens
      </p>
      {durations.length > 0 && (
        <ul className="mt-2 space-y-1">
          {durations.map((stage) => (
            <li key={stage.stage} className="flex items-center gap-2 text-xs text-ink-muted">
              <span className="w-16 capitalize">{stage.stage}</span>
              <span className="h-1 flex-1 overflow-hidden rounded bg-accent-soft">
                <span
                  className="block h-full rounded bg-accent"
                  style={{ width: `${Math.max(4, ((stage.duration_ms ?? 0) / max) * 100)}%` }}
                />
              </span>
              <span className="tabular-nums">{formatDuration(stage.duration_ms)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function RetrievedChunks({ chunks, citedIds }: { chunks: RetrievedChunk[]; citedIds: Map<string, string> }) {
  if (chunks.length === 0) {
    return <p className="text-xs text-ink-muted">No retrieved chunks reported.</p>
  }
  return (
    <section data-testid="trace-chunks" aria-label="Retrieved chunks">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Retrieved</h3>
      <ul className="mt-2 space-y-2">
        {chunks.map((chunk, index) => (
          <li
            key={`${chunk.chunk_id}-${index}`}
            data-testid={`trace-chunk-${index}`}
            className="rounded-lg border border-line p-2"
          >
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="truncate font-medium text-ink">{chunk.source_file}</span>
              {chunk.cited && (
                <span className="rounded bg-badge px-1 text-[10px] font-medium text-badge-ink">
                  {citedIds.get(chunk.chunk_id) ?? 'cited'}
                </span>
              )}
            </div>
            <p className="mt-0.5 truncate text-[11px] text-ink-muted">{chunk.section_path}</p>
            <p className="mt-1 line-clamp-2 text-xs leading-snug text-ink-muted">{chunk.excerpt}</p>
            <p className="mt-1 text-[11px] text-ink-muted">
              dense {chunk.dense_rank ?? '–'} · bm25 {chunk.bm25_rank ?? '–'} · fused{' '}
              {chunk.fused_score.toFixed(3)}
            </p>
          </li>
        ))}
      </ul>
    </section>
  )
}

function ToolCalls({ calls }: { calls: ToolCallInfo[] }) {
  if (calls.length === 0) return null
  return (
    <section data-testid="trace-tools" aria-label="Tool calls">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Tools</h3>
      <ul className="mt-2 space-y-1">
        {calls.map((call, index) => (
          <li key={`${call.tool}-${index}`} className="flex items-center gap-2 text-xs text-ink-muted">
            <span className="font-medium text-ink">{call.tool}</span>
            <span className="truncate">{JSON.stringify(call.arguments)}</span>
            <span className={`ml-auto rounded px-1 text-[10px] ${call.status === 'ok' ? 'bg-sage/15 text-sage' : 'bg-champagne/50 text-ink'}`}>
              {call.status}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function ReviewSummary({ review }: { review: ReviewInfo }) {
  const flags = review.unsupported_claims.length + review.ambiguity_flags.length
  return (
    <section data-testid="trace-review" aria-label="Review summary" className="text-xs text-ink-muted">
      Verdict: <span className="font-medium text-ink">{review.verdict}</span>
      {flags > 0 && ` · ${flags} flag(s)`}
    </section>
  )
}

interface TracePanelProps {
  turn: Turn | null
}

/** Basic trace panel (Phase C): index status, metrics and retrieved chunks. */
export function TracePanel({ turn }: TracePanelProps) {
  const health = useHealth()
  const response = turn?.response

  return (
    <div data-testid="trace-panel" className="scope-dark flex h-full flex-col gap-4 p-4 text-ink">
      <IndexStatus health={health} />
      {response ? (
        <>
          <QueryMetrics trace={response.trace ?? []} latencyMs={response.latency_ms} usage={response.usage} />
          <RetrievedChunks
            chunks={response.retrieval?.chunks ?? []}
            citedIds={new Map(response.citations.map((citation) => [citation.chunk_id, citation.id]))}
          />
          <ToolCalls calls={response.tool_calls} />
          <ReviewSummary review={response.review} />
        </>
      ) : (
        <p className="text-xs text-ink-muted">No query yet. Ask a question to see the pipeline trace.</p>
      )}
    </div>
  )
}
