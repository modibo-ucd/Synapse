import { ApiErrorPayloadSchema, AskResponseSchema, type AskResponse } from '../types/api'

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
