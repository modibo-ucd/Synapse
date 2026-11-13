import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { useHistoryStore } from './stores/history'

vi.mock('./lib/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./lib/api/client')>()
  return {
    ...actual,
    askQuestion: vi.fn(),
    getHealth: vi.fn(async () => ({ status: 'ok', index: 'ready', llm_configured: true })),
  }
})

describe('App', () => {
  beforeEach(() => {
    window.localStorage.clear()
    useHistoryStore.setState({ sessions: [], activeSessionId: null })
  })

  it('shows the composer and the medical disclaimer on first load', async () => {
    render(<App />)
    expect(screen.getByTestId('question-input')).toBeInTheDocument()
    expect(screen.getByTestId('medical-disclaimer')).toHaveTextContent(/not medical advice/i)
    // Flush the async /health poll so the footer and trace panel settle.
    await screen.findAllByText('Index ready')
  })

  it('shows the empty state with the public questions', async () => {
    render(<App />)
    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.getByTestId('example-ex1')).toBeInTheDocument()
    await screen.findAllByText('Index ready')
  })
})
