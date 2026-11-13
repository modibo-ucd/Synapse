import { useCallback, useState } from 'react'

import { ApiError, askQuestion, streamAskQuestion } from '../../lib/api/client'
import type { AskResponse, StageEvent } from '../../types/api'

export type ChatStatus = 'idle' | 'loading' | 'success' | 'error'

export interface ChatState {
  status: ChatStatus
  question: string
  answer: AskResponse | null
  error: string | null
  trace: StageEvent[] | null
}

const initialState: ChatState = {
  status: 'idle',
  question: '',
  answer: null,
  error: null,
  trace: null,
}

export function useChat() {
  const [state, setState] = useState<ChatState>(initialState)

  const submit = useCallback(async (question: string) => {
    const trimmed = question.trim()
    if (!trimmed) {
      return
    }
    setState({ status: 'loading', question: trimmed, answer: null, error: null, trace: [] })

    try {
      const stages: StageEvent[] = []
      for await (const event of streamAskQuestion(trimmed)) {
        if (event.type === 'stage') {
          stages.push(event.event)
          setState((previous) => ({ ...previous, trace: [...stages] }))
        } else if (event.type === 'result') {
          setState({
            status: 'success',
            question: trimmed,
            answer: event.result,
            error: null,
            trace: stages,
          })
          return
        } else {
          throw event.error
        }
      }
      throw new ApiError('stream_incomplete', 'The stream ended without a result.')
    } catch {
      // Streaming failed; fall back to the plain /ask endpoint (hide the trace panel).
      setState((previous) => ({ ...previous, trace: null }))
      try {
        const answer = await askQuestion(trimmed)
        setState({ status: 'success', question: trimmed, answer, error: null, trace: null })
      } catch (fallbackError) {
        const message =
          fallbackError instanceof ApiError
            ? fallbackError.message
            : 'Something went wrong. Please try again.'
        setState({ status: 'error', question: trimmed, answer: null, error: message, trace: null })
      }
    }
  }, [])

  const reset = useCallback(() => setState(initialState), [])

  return { state, submit, reset }
}
