import { z } from 'zod'

import { ApiError, isAbortError, parseApiError } from './client'
import { ApiErrorPayloadSchema, AskResponseSchema } from './schemas'
import type { AskResponse, StageTrace } from '../../types/api'

/** A parsed server-sent event from `POST /ask/stream`. */
export type StreamEvent =
  | { type: 'stage'; data: StageTrace }
  | { type: 'result'; data: AskResponse }
  | { type: 'error'; data: { code: string; message: string; request_id?: string | null } }

/** Stall the stream (and fall back) if no event arrives within this window. */
export const STREAM_INACTIVITY_TIMEOUT_MS = 10_000

const STAGE_NAMES = ['plan', 'retrieve', 'tools', 'review', 'answer'] as const

/** Wire shape the backend emits for a live stage event (`status` is `ok|skipped`). */
const StreamStageSchema = z.object({
  stage: z.enum(STAGE_NAMES),
  status: z.enum(['ok', 'skipped', 'running', 'error', 'done']),
  duration_ms: z.number(),
  summary: z.string().default(''),
})

type StreamStage = z.infer<typeof StreamStageSchema>

/** Maps the backend's `ok` status to the UI timeline's `done` (keeps `running`/`error` if sent). */
function toStageTrace(raw: StreamStage): StageTrace {
  let status: StageTrace['status']
  if (raw.status === 'ok') status = 'done'
  else if (raw.status === 'running') status = 'running'
  else if (raw.status === 'error') status = 'error'
  else status = 'skipped'
  return { stage: raw.stage, status, duration_ms: raw.duration_ms, summary: raw.summary }
}

/**
 * Incremental SSE parser. Feed raw byte chunks; it buffers partial events
 * (including multi-byte characters split across chunks) and returns complete,
 * valid events. Comment lines, unknown events and malformed JSON are skipped.
 */
export class SSEParser {
  private buffer = ''
  private readonly decoder = new TextDecoder('utf-8')

  push(chunk: Uint8Array): StreamEvent[] {
    this.buffer += this.decoder.decode(chunk, { stream: true })
    return this.drain()
  }

  private drain(): StreamEvent[] {
    const events: StreamEvent[] = []
    let boundary = this.buffer.indexOf('\n\n')
    while (boundary !== -1) {
      const raw = this.buffer.slice(0, boundary)
      this.buffer = this.buffer.slice(boundary + 2)
      const event = this.parseBlock(raw)
      if (event) events.push(event)
      boundary = this.buffer.indexOf('\n\n')
    }
    return events
  }

  private parseBlock(raw: string): StreamEvent | null {
    let name = 'message'
    const dataLines: string[] = []
    for (const rawLine of raw.split('\n')) {
      const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine
      if (line === '' || line.startsWith(':')) continue
      if (line.startsWith('event:')) name = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''))
    }
    if (dataLines.length === 0) return null
    return this.deserialize(name, dataLines.join('\n'))
  }

  private deserialize(name: string, data: string): StreamEvent | null {
    let json: unknown
    try {
      json = JSON.parse(data)
    } catch {
      return null
    }
    if (name === 'stage') {
      const parsed = StreamStageSchema.safeParse(json)
      return parsed.success ? { type: 'stage', data: toStageTrace(parsed.data) } : null
    }
    if (name === 'result') {
      const parsed = AskResponseSchema.safeParse(json)
      return parsed.success ? { type: 'result', data: parsed.data } : null
    }
    if (name === 'error') {
      const parsed = ApiErrorPayloadSchema.safeParse(json)
      return parsed.success ? { type: 'error', data: parsed.data.error } : null
    }
    return null
  }
}

async function streamErrorFrom(response: Response): Promise<ApiError> {
  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }
  return parseApiError(payload)
}

/**
 * Streams `POST /ask/stream`, invoking `onStage` for each stage event and
 * resolving with the final `result`. Throws `ApiError` on HTTP errors, server
 * `error` events, a stalled stream, or a stream that ends without a result.
 */
export async function streamAsk(
  question: string,
  onStage: (stage: StageTrace) => void,
  signal?: AbortSignal,
): Promise<AskResponse> {
  let response: Response
  try {
    response = await fetch('/ask/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      signal,
    })
  } catch (error) {
    if (isAbortError(error)) throw error
    throw new ApiError('network_error', 'Could not reach the server. Please try again.')
  }

  if (!response.ok) throw await streamErrorFrom(response)
  if (!response.body) throw new ApiError('network_error', 'The server returned an empty stream.')

  const reader = response.body.getReader()
  const parser = new SSEParser()
  let result: AskResponse | null = null
  let timer: ReturnType<typeof setTimeout> | undefined

  const resetTimer = () => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      void reader.cancel().catch(() => {})
    }, STREAM_INACTIVITY_TIMEOUT_MS)
  }
  resetTimer()

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      const events = parser.push(value)
      if (events.length > 0) resetTimer()
      for (const event of events) {
        if (event.type === 'result') result = event.data
        else if (event.type === 'error') {
          throw new ApiError(
            event.data.code,
            event.data.message,
            event.data.request_id ?? undefined,
          )
        } else onStage(event.data)
      }
    }
  } finally {
    if (timer) clearTimeout(timer)
  }

  if (!result) throw new ApiError('invalid_response', 'The stream ended without a result.')
  return result
}
