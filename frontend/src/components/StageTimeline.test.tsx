import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { StageTimeline } from './StageTimeline'
import type { Turn } from '../types/ui'

function turn(overrides: Partial<Turn>): Turn {
  return { id: 't1', question: 'q', createdAt: 0, status: 'pending', ...overrides }
}

describe('StageTimeline', () => {
  it('shows an indeterminate state when pending with no live events', () => {
    render(<StageTimeline turn={turn({ status: 'pending' })} />)
    expect(screen.getByTestId('stage-timeline')).toBeInTheDocument()
    expect(screen.getByText(/Working/)).toBeInTheDocument()
  })

  it('renders the five stages using only real events', () => {
    render(
      <StageTimeline
        turn={turn({
          status: 'pending',
          liveStages: [
            { stage: 'plan', status: 'done', duration_ms: 10, summary: 'simple' },
            { stage: 'retrieve', status: 'done', duration_ms: 5, summary: '2 chunks' },
          ],
        })}
      />,
    )
    expect(screen.getByText('Analyzing your question')).toBeInTheDocument()
    expect(screen.getByText('Searching sources (semantic + keyword)')).toBeInTheDocument()
    expect(screen.getByText('Consulting local tools')).toBeInTheDocument()
  })

  it('collapses to a one-line summary when done and re-expands', async () => {
    const user = userEvent.setup()
    render(
      <StageTimeline
        turn={turn({
          status: 'done',
          response: {
            answer: 'a',
            sources: ['a.md', 'b.md', 'c.md'],
            citations: [],
            disclaimer: 'd',
            tool_calls: [],
            review: { verdict: 'pass', unsupported_claims: [], ambiguity_flags: [] },
            retrieval_mode: 'hybrid',
            trace_id: 'x',
            usage: { tokens_in: 1, tokens_out: 2 },
            latency_ms: 8400,
            trace: [
              { stage: 'plan', status: 'done', duration_ms: 10, summary: 'simple' },
              { stage: 'retrieve', status: 'done', duration_ms: 5, summary: '2 chunks' },
              { stage: 'tools', status: 'done', duration_ms: 5, summary: '1 claim' },
              { stage: 'review', status: 'done', duration_ms: 5, summary: 'pass' },
              { stage: 'answer', status: 'done', duration_ms: 5, summary: '1 source' },
            ],
          },
        })}
      />,
    )
    const summary = screen.getByRole('button')
    expect(summary).toHaveTextContent('Answered in 8.4 s')
    expect(summary).toHaveTextContent('5 stages')
    expect(summary).toHaveTextContent('3 sources')
    await user.click(summary)
    expect(screen.getByText('Analyzing your question')).toBeInTheDocument()
  })
})
