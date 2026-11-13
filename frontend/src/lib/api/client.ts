import { ApiErrorPayloadSchema, AskResponseSchema, HealthResponseSchema, SourceDocumentSchema } from './schemas'
import type { AskResponse, HealthResponse, SourceDocument } from '../../types/api'

const REQUEST_TIMEOUT_MS = 120_000
const HEALTH_TIMEOUT_MS = 10_000

/** Typed, user-facing API error. Never leaks provider payloads. */
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

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

export function parseApiError(payload: unknown): ApiError {
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

async function performFetch(
  path: string,
  init: RequestInit,
  timeoutMs: number,
  signal?: AbortSignal,
): Promise<Response> {
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  const onExternalAbort = () => controller.abort()
  if (signal) {
    if (signal.aborted) controller.abort()
    else signal.addEventListener('abort', onExternalAbort, { once: true })
  }

  try {
    return await fetch(path, { ...init, signal: controller.signal })
  } catch (error) {
    if (isAbortError(error)) {
      throw new ApiError(
        timedOut ? 'timeout' : 'aborted',
        timedOut ? 'The request timed out. Please try again.' : 'The request was cancelled.',
      )
    }
    throw new ApiError('network_error', 'Could not reach the server. Please try again.')
  } finally {
    clearTimeout(timer)
    if (signal) signal.removeEventListener('abort', onExternalAbort)
  }
}

async function errorFrom(response: Response): Promise<ApiError> {
  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }
  return parseApiError(payload)
}

/** Non-streaming `POST /ask`; cancellable via the optional signal. */
export async function askQuestion(question: string, signal?: AbortSignal): Promise<AskResponse> {
  const response = await performFetch(
    '/ask',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    },
    REQUEST_TIMEOUT_MS,
    signal,
  )
  if (!response.ok) throw await errorFrom(response)
  const data: unknown = await response.json()
  const parsed = AskResponseSchema.safeParse(data)
  if (!parsed.success) {
    throw new ApiError('invalid_response', 'The server returned an unexpected response shape.')
  }
  return parsed.data
}

/** `GET /health` — index status, LLM config, version and index stats. */
export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await performFetch('/health', { method: 'GET' }, HEALTH_TIMEOUT_MS, signal)
  if (!response.ok) throw await errorFrom(response)
  const data: unknown = await response.json()
  const parsed = HealthResponseSchema.safeParse(data)
  if (!parsed.success) {
    throw new ApiError('invalid_response', 'The server returned an unexpected response shape.')
  }
  return parsed.data
}

const SOURCE_TIMEOUT_MS = 30_000

export interface SourceFetchResult {
  /** `null` when the server answered 304 — the caller reuses its cached copy. */
  document: SourceDocument | null
  etag: string | null
}

/**
 * `GET /api/v1/sources/{file_name}` with optional ETag revalidation. A 304 is
 * surfaced as `{ document: null, etag }` rather than an error.
 */
export async function getSourceDocument(
  fileName: string,
  etag?: string,
  signal?: AbortSignal,
): Promise<SourceFetchResult> {
  const headers: Record<string, string> = {}
  if (etag) headers['If-None-Match'] = etag
  const response = await performFetch(
    `/api/v1/sources/${encodeURIComponent(fileName)}`,
    { method: 'GET', headers },
    SOURCE_TIMEOUT_MS,
    signal,
  )
  if (response.status === 304) return { document: null, etag: etag ?? null }
  if (!response.ok) throw await errorFrom(response)
  const data: unknown = await response.json()
  const parsed = SourceDocumentSchema.safeParse(data)
  if (!parsed.success) {
    throw new ApiError('invalid_response', 'The server returned an unexpected response shape.')
  }
  return { document: parsed.data, etag: response.headers.get('ETag') }
}
