import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { StageEvent } from '../types/api'
import { TracePanel } from './TracePanel'

const recorded: StageEvent[] = [
  {
    stage: 'plan',
    status: 'ok',
    duration_ms: 120,
    summary: 'simple, 1 sub-goal(s)',
    details: {
      complexity: 'simple',
      in_scope: true,
      sub_goals: [
        { id: 'sg1', question: 'warfarin contraindications', intent: '', entities: ['warfarin'] },
      ],
    },
  },
  {
    stage: 'retrieve',
    status: 'ok',
    duration_ms: 80,
    summary: '1 chunk(s) from 1 file(s) (hybrid)',
    details: {
      mode: 'hybrid',
      chunk_count: 1,
      source_files: ['dailymed-warfarin.md'],
      chunks: [
        {
          source_file: 'dailymed-warfarin.md',
          section: '4 CONTRAINDICATIONS',
          dense_rank: 1,
          bm25_rank: 1,
          fused_score: 0.03,
        },
      ],
    },
  },
]

describe('TracePanel', () => {
  it('renders the five stages with expandable details from recorded events', () => {
    render(<TracePanel events={recorded} loading={true} />)
    expect(screen.getByText('Plan')).toBeInTheDocument()
    expect(screen.getByText('Retrieve')).toBeInTheDocument()
    expect(screen.getByText('Tools')).toBeInTheDocument()
    expect(screen.getByText('Review')).toBeInTheDocument()
    expect(screen.getByText('Answer')).toBeInTheDocument()

    expect(screen.getByText(/warfarin contraindications/)).toBeInTheDocument()
    expect(screen.getAllByText(/dailymed-warfarin\.md/).length).toBeGreaterThan(0)
  })

  it('collapses the stage list when the toggle is clicked', async () => {
    render(<TracePanel events={recorded} loading={false} />)
    const toggle = screen.getByTestId('trace-toggle')
    expect(screen.getByText('Retrieve')).toBeInTheDocument()
    await userEvent.click(toggle)
    expect(screen.queryByText('Retrieve')).not.toBeInTheDocument()
  })
})
