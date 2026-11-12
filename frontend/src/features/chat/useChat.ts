import { useCallback, useState } from 'react'

import { ApiError, askQuestion } from '../../lib/api'
import type { AskResponse } from '../../types/api'

export type ChatStatus = 'idle' | 'loading' | 'success' | 'error'

export interface ChatState {
  status: ChatStatus
  question: string
  answer: AskResponse | null
  error: string | null
}

const initialState: ChatState = {
  status: 'idle',
  question: '',
  answer: null,
  error: null,
}

export function useChat() {
  const [state, setState] = useState<ChatState>(initialState)

  const submit = useCallback(async (question: string) => {
    const trimmed = question.trim()
    if (!trimmed) {
      return
    }
    setState({ status: 'loading', question: trimmed, answer: null, error: null })
    try {
      const answer = await askQuestion(trimmed)
      setState({ status: 'success', question: trimmed, answer, error: null })
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Something went wrong. Please try again.'
      setState({ status: 'error', question: trimmed, answer: null, error: message })
    }
  }, [])

  const reset = useCallback(() => setState(initialState), [])

  return { state, submit, reset }
}
