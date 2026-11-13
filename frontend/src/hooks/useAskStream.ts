import { useCallback, useRef } from 'react'

import { ApiError, askQuestion, isAbortError } from '../lib/api/client'
import { streamAsk } from '../lib/api/stream'
import type { AskResponse, StageTrace } from '../types/api'

export interface AskStreamHandlers {
  onStage: (stage: StageTrace) => void
  onResult: (response: AskResponse) => void
  onError: (error: ApiError) => void
}

export interface AskStreamController {
  start: (question: string, handlers: AskStreamHandlers) => Promise<void>
  stop: () => void
}

/**
 * Streaming ask with a silent one-shot fallback to `POST /ask`. Stage events
 * stream live; any streaming failure (HTTP error, parse error, server error,
 * stall) falls back to the non-streaming endpoint exactly once. A user abort
 * is surfaced as an `aborted` ApiError instead of triggering the fallback.
 */
export function useAskStream(): AskStreamController {
  const controllerRef = useRef<AbortController | null>(null)

  const stop = useCallback(() => {
    controllerRef.current?.abort()
  }, [])

  const start = useCallback(
    async (question: string, handlers: AskStreamHandlers) => {
      stop()
      const controller = new AbortController()
      controllerRef.current = controller
      try {
        let response: AskResponse
        try {
          response = await streamAsk(question, handlers.onStage, controller.signal)
        } catch (streamError) {
          if (isAbortError(streamError)) throw streamError
          response = await askQuestion(question, controller.signal)
        }
        handlers.onResult(response)
      } catch (error) {
        if (isAbortError(error)) {
          handlers.onError(new ApiError('aborted', 'The request was cancelled.'))
        } else if (error instanceof ApiError) {
          handlers.onError(error)
        } else {
          handlers.onError(new ApiError('unknown_error', 'Something went wrong. Please try again.'))
        }
      } finally {
        if (controllerRef.current === controller) controllerRef.current = null
      }
    },
    [stop],
  )

  return { start, stop }
}
