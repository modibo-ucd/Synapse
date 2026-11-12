import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, askQuestion, streamAskQuestion } from '../../lib/api'
import type { AskResponse } from '../../types/api'
import { ChatPage } from './ChatPage'

vi.mock('../../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api')>()
  return { ...actual, askQuestion: vi.fn(), streamAskQuestion: vi.fn() }
})

const mockedAsk = vi.mocked(askQuestion)
const mockedStream = vi.mocked(streamAskQuestion)

const validResponse: AskResponse = {
  answer: 'warfarin is contraindicated in pregnancy [S1]\n\nNot medical advice.',
  sources: ['dailymed-warfarin.md'],
  citations: [
    {
      id: 'S1',
      source_file: 'dailymed-warfarin.md',
      section: '4 CONTRAINDICATIONS',
      chunk_id: 'c1',
      excerpt: 'warfarin is contraindicated in pregnancy',
    },
  ],
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
    mockedAsk.mockReset()
    mockedStream.mockReset()
    // Default: streaming reports an error, so requests fall back to /ask.
    mockedStream.mockImplementation(async function* () {
      yield { type: 'error', error: new ApiError('stream_unavailable', 'Streaming is not available.') }
    })
  })

  it('shows the API error message when the request fails', async () => {
    mockedAsk.mockRejectedValue(new ApiError('provider_error', 'The LLM endpoint failed.'))
    render(<ChatPage />)
    await userEvent.type(screen.getByTestId('question-input'), 'warfarin')
    await userEvent.click(screen.getByTestId('submit-button'))
    expect(await screen.findByTestId('error')).toBeInTheDocument()
    expect(screen.getByText('The LLM endpoint failed.')).toBeInTheDocument()
  })

  it('fills the input when an example is clicked', async () => {
    render(<ChatPage />)
    await userEvent.click(screen.getByTestId('example-ex1'))
    expect(screen.getByTestId('question-input')).toHaveValue(
      'What are the main contraindications for warfarin?',
    )
  })

  it('shows a working indicator while the request is pending', async () => {
    mockedAsk.mockImplementation(() => new Promise<never>(() => {}))
    render(<ChatPage />)
    await userEvent.type(screen.getByTestId('question-input'), 'warfarin')
    await userEvent.click(screen.getByTestId('submit-button'))
    expect(screen.getByTestId('loading')).toBeInTheDocument()
  })

  it('falls back to plain /ask when streaming fails', async () => {
    mockedAsk.mockResolvedValue(validResponse)
    render(<ChatPage />)
    await userEvent.type(screen.getByTestId('question-input'), 'warfarin')
    await userEvent.click(screen.getByTestId('submit-button'))
    expect(await screen.findByTestId('answer')).toBeInTheDocument()
    expect(mockedAsk).toHaveBeenCalledWith('warfarin')
  })
})

