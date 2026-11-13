import { render, screen } from '@testing-library/react'
import type { RefObject } from 'react'
import { describe, expect, it } from 'vitest'

import type { AskResponse } from '../../types/api'
import type { Turn } from '../../types/ui'
import { AnswerCard } from './AnswerCard'

const noScroller: RefObject<HTMLElement | null> = { current: null }

function makeResponse(overrides: Partial<AskResponse> = {}): AskResponse {
  return {
    answer: 'Warfarin is contraindicated in pregnancy.',
    sources: ['dailymed-warfarin.md'],
    citations: [],
    disclaimer: 'Not medical advice.',
    tool_calls: [],
    review: { verdict: 'pass', unsupported_claims: [], ambiguity_flags: [] },
    retrieval_mode: 'hybrid',
    trace_id: 't1',
    usage: { tokens_in: 10, tokens_out: 20 },
    latency_ms: 100,
    ...overrides,
  }
}

function makeTurn(status: Turn['status'], response?: AskResponse, error?: string): Turn {
  return { id: 'turn-1', question: 'q?', createdAt: Date.now(), status, response, error }
}

describe('AnswerCard', () => {
  it('shows the medical disclaimer in every answer', () => {
    render(<AnswerCard turn={makeTurn('done', makeResponse())} scrollerRef={noScroller} />)
    expect(screen.getByTestId('medical-disclaimer')).toHaveTextContent(/not medical advice/i)
  })

  it('labels a pass verdict as "Grounding check passed"', () => {
    render(<AnswerCard turn={makeTurn('done', makeResponse())} scrollerRef={noScroller} />)
    expect(screen.getByTestId('grounding-chip')).toHaveTextContent('Grounding check passed')
  })

  it('labels a revise verdict as "Review notes" and lists flags', () => {
    render(
      <AnswerCard
        turn={makeTurn(
          'done',
          makeResponse({
            review: { verdict: 'revise', unsupported_claims: ['claim'], ambiguity_flags: [] },
          }),
        )}
        scrollerRef={noScroller}
      />,
    )
    expect(screen.getByTestId('grounding-chip')).toHaveTextContent('Review notes')
    expect(screen.getByTestId('review-notes')).toHaveTextContent('Unsupported claim: claim')
  })

  it('shows the reading time only for long answers', () => {
    render(
      <AnswerCard
        turn={makeTurn('done', makeResponse({ answer: 'word '.repeat(70) }))}
        scrollerRef={noScroller}
      />,
    )
    expect(screen.getByTestId('reading-time')).toBeInTheDocument()
  })

  it('renders the pending and error states', () => {
    const { rerender } = render(<AnswerCard turn={makeTurn('pending')} scrollerRef={noScroller} />)
    expect(screen.getByTestId('answer-pending')).toBeInTheDocument()
    rerender(<AnswerCard turn={makeTurn('error', undefined, 'boom')} scrollerRef={noScroller} />)
    expect(screen.getByTestId('answer-error')).toHaveTextContent('boom')
  })
})
