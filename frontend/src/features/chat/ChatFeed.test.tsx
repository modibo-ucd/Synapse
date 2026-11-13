import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { Turn } from '../../types/ui'
import { ChatFeed } from './ChatFeed'

const turn: Turn = {
  id: 't1',
  question: 'warfarin?',
  createdAt: Date.now(),
  status: 'error',
  error: 'boom',
}

describe('ChatFeed', () => {
  it('renders the empty state with the 4 public questions and the hint', () => {
    render(<ChatFeed turns={[]} onSelectExample={() => {}} />)
    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.getByTestId('example-ex1')).toBeInTheDocument()
    expect(screen.getByTestId('example-ex4')).toBeInTheDocument()
    expect(screen.getByTestId('independence-hint')).toBeInTheDocument()
  })

  it('renders a user bubble and answer card per turn', () => {
    render(<ChatFeed turns={[turn]} onSelectExample={() => {}} />)
    expect(screen.getByTestId('user-bubble')).toHaveTextContent('warfarin?')
    expect(screen.getByTestId('answer-error')).toHaveTextContent('boom')
  })

  it('forwards example selection', async () => {
    const onSelectExample = vi.fn()
    render(<ChatFeed turns={[]} onSelectExample={onSelectExample} />)
    await userEvent.click(screen.getByTestId('example-ex1'))
    expect(onSelectExample).toHaveBeenCalledWith(
      'What are the main contraindications for warfarin?',
    )
  })
})
