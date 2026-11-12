import {
  ApiErrorPayloadSchema,
  AskResponseSchema,
  StageEventSchema,
  type AskResponse,
  type StageEvent,
} from '../types/api'

const REQUEST_TIMEOUT_MS = 120_000

export class ApiError extends Error {
  readonly code: string
  readonly requestId?: string

  constructor(code: string, message: string, requestId?: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.requestId = requestId
    Object.setPrototypeOf(this, new.target.prototype)
  }
}

function parseApiError(payload: unknown): ApiError {
  const parsed = ApiErrorPayloadSchema.safeParse(payload)
  if (parsed.success) {
    return new ApiError(
      parsed.data.error.code,
      parsed.data.error.message,
      parsed.data.error.request_id ?? undefined,
    )
  }
  return new ApiError('unknown_error', 'The server returned an unexpected error.')
}

async function performRequest(question: string, signal: AbortSignal): Promise<AskResponse> {
  let response: Response
  try {
    response = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }
    throw new ApiError('network_error', 'Could not reach the server. Please try again.')
  }

  if (!response.ok) {
    let payload: unknown = null
    try {
      payload = await response.json()
    } catch {
      payload = null
    }
    throw parseApiError(payload)
  }

  const data: unknown = await response.json()
  const parsed = AskResponseSchema.safeParse(data)
  if (!parsed.success) {
    throw new ApiError('invalid_response', 'The server returned an unexpected response shape.')
  }
  return parsed.data
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    return await performRequest(question, controller.signal)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('timeout', 'The request timed out. Please try again.')
    }
    throw error
  } finally {
    clearTimeout(timer)
  }
}

export type StreamEvent =
  | { type: 'stage'; event: StageEvent }
  | { type: 'result'; result: AskResponse }
  | { type: 'error'; error: ApiError }

function parseSseEvent(raw: string): StreamEvent | null {
  let eventName = 'message'
  let data = ''
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) {
      eventName = line.slice('event:'.length).trim()
    } else if (line.startsWith('data:')) {
      data += line.slice('data:'.length).trim()
    }
  }
  if (!data) {
    return null
  }
  try {
    const parsed: unknown = JSON.parse(data)
    if (eventName === 'stage') {
      return { type: 'stage', event: StageEventSchema.parse(parsed) }
    }
    if (eventName === 'result') {
      return { type: 'result', result: AskResponseSchema.parse(parsed) }
    }
    if (eventName === 'error') {
      return { type: 'error', error: parseApiError(parsed) }
    }
  } catch {
    return null
  }
  return null
}

export async function* streamAskQuestion(question: string): AsyncGenerator<StreamEvent> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  let response: Response
  try {
    response = await fetch('/ask/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      signal: controller.signal,
    })
  } catch (error) {
    clearTimeout(timer)
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('timeout', 'The request timed out. Please try again.')
    }
    throw new ApiError('network_error', 'Could not reach the server. Please try again.')
  }

  if (!response.ok) {
    clearTimeout(timer)
    let payload: unknown = null
    try {
      payload = await response.json()
    } catch {
      payload = null
    }
    throw parseApiError(payload)
  }
  if (!response.body) {
    clearTimeout(timer)
    throw new ApiError('stream_unavailable', 'Streaming is not available.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }
      buffer += decoder.decode(value, { stream: true })
      let boundary = buffer.indexOf('\n\n')
      while (boundary >= 0) {
        const raw = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        const event = parseSseEvent(raw)
        if (event) {
          yield event
        }
        boundary = buffer.indexOf('\n\n')
      }
    }
  } finally {
    clearTimeout(timer)
    reader.releaseLock()
  }
}
