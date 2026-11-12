import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, askQuestion } from '../../lib/api'
import { ChatPage } from './ChatPage'

vi.mock('../../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api')>()
  return { ...actual, askQuestion: vi.fn() }
})

const mockedAsk = vi.mocked(askQuestion)

describe('ChatPage', () => {
  beforeEach(() => {
    mockedAsk.mockReset()
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
})
