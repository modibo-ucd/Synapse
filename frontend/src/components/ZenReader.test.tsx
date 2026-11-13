import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ZenReader } from './ZenReader'
import { setZenTrigger } from '../lib/zenFocus'
import type { AskResponse } from '../types/api'
import type { Turn } from '../types/ui'

function makeResponse(): AskResponse {
  return {
    answer: 'Warfarin answer.',
    sources: ['dailymed-warfarin.md'],
    citations: [],
    disclaimer: 'Not medical advice.',
    tool_calls: [],
    review: { verdict: 'pass', unsupported_claims: [], ambiguity_flags: [] },
    retrieval_mode: 'hybrid',
    trace_id: 't1',
    usage: { tokens_in: 10, tokens_out: 20 },
    latency_ms: 100,
  }
}

function makeTurn(): Turn {
  return {
    id: 'turn-1',
    question: 'What are the contraindications?',
    createdAt: Date.now(),
    status: 'done',
    response: makeResponse(),
  }
}

describe('ZenReader', () => {
  it('shows the answer, disclaimer and sources', () => {
    render(<ZenReader turn={makeTurn()} onClose={vi.fn()} />)
    expect(screen.getByTestId('zen-reader')).toBeInTheDocument()
    expect(screen.getByText('Warfarin answer.')).toBeInTheDocument()
    expect(screen.getByTestId('medical-disclaimer')).toBeInTheDocument()
  })

  it('closes on Escape and returns focus to the zen trigger', async () => {
    const user = userEvent.setup()
    const trigger = document.createElement('button')
    document.body.appendChild(trigger)
    setZenTrigger(trigger)
    const onClose = vi.fn()
    render(<ZenReader turn={makeTurn()} onClose={onClose} />)
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
    expect(document.activeElement).toBe(trigger)
    trigger.remove()
  })

  it('closes via the Exit focus button', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<ZenReader turn={makeTurn()} onClose={onClose} />)
    await user.click(screen.getByTestId('zen-exit'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
