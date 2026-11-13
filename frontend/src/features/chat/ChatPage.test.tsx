import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, askQuestion, getHealth } from '../../lib/api/client'
import { useHistoryStore } from '../../stores/history'
import type { AskResponse } from '../../types/api'
import { ChatPage } from './ChatPage'

vi.mock('../../lib/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api/client')>()
  return { ...actual, askQuestion: vi.fn(), getHealth: vi.fn() }
})

const mockedAsk = vi.mocked(askQuestion)
const mockedHealth = vi.mocked(getHealth)

const validResponse: AskResponse = {
  answer: 'warfarin is contraindicated in pregnancy [S1]',
  sources: ['dailymed-warfarin.md'],
  citations: [],
  disclaimer: 'Not medical advice.',
  plan: { complexity: 'simple', in_scope: true, sub_goals: [] },
  tool_calls: [],
  review: { verdict: 'pass', unsupported_claims: [], ambiguity_flags: [] },
  retrieval_mode: 'hybrid',
  trace_id: 't1',
  usage: { tokens_in: 10, tokens_out: 20 },
  latency_ms: 100,
}

describe('ChatPage', () => {
  beforeEach(() => {
    window.localStorage.clear()
    useHistoryStore.setState({ sessions: [], activeSessionId: null })
    mockedAsk.mockReset()
    mockedHealth.mockReset()
    mockedHealth.mockResolvedValue({ status: 'ok', index: 'ready', llm_configured: true })
  })

  it('sends a question and renders the answer with the disclaimer', async () => {
    mockedAsk.mockResolvedValue(validResponse)
    render(<ChatPage />)
    await userEvent.type(screen.getByTestId('question-input'), 'warfarin')
    await userEvent.click(screen.getByTestId('submit-button'))
    expect(await screen.findByTestId('answer-card')).toBeInTheDocument()
    expect(screen.getByTestId('medical-disclaimer')).toHaveTextContent(/not medical advice/i)
  })

  it('persists the turn into the history store', async () => {
    mockedAsk.mockResolvedValue(validResponse)
    render(<ChatPage />)
    await userEvent.type(screen.getByTestId('question-input'), 'warfarin')
    await userEvent.click(screen.getByTestId('submit-button'))
    await screen.findByTestId('answer-card')
    const session = useHistoryStore.getState().sessions[0]
    expect(session).toBeDefined()
    expect(session?.turns[0]?.question).toBe('warfarin')
    expect(session?.turns[0]?.status).toBe('done')
  })

  it('fills and sends when an example is clicked', async () => {
    mockedAsk.mockResolvedValue(validResponse)
    render(<ChatPage />)
    await userEvent.click(screen.getByTestId('example-ex1'))
    expect(mockedAsk).toHaveBeenCalledWith(
      'What are the main contraindications for warfarin?',
      expect.anything(),
    )
    expect(await screen.findByTestId('answer-card')).toBeInTheDocument()
  })

  it('shows the API error message when the request fails', async () => {
    mockedAsk.mockRejectedValue(new ApiError('provider_error', 'The LLM endpoint failed.'))
    render(<ChatPage />)
    await userEvent.type(screen.getByTestId('question-input'), 'warfarin')
    await userEvent.click(screen.getByTestId('submit-button'))
    expect(await screen.findByTestId('answer-error')).toHaveTextContent('The LLM endpoint failed.')
  })
})
