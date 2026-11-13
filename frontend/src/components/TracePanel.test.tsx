import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { AskResponse } from '../types/api'
import type { Turn } from '../types/ui'
import { TracePanel } from './TracePanel'

vi.mock('../lib/api/client', () => ({
  getHealth: vi.fn(async () => ({
    status: 'ok',
    index: 'ready',
    llm_configured: true,
    version: '0.1.0',
    index_stats: { files: 21, chunks: 300, embedding_model: 'text-embedding-3-small' },
  })),
}))

function makeResponse(): AskResponse {
  return {
    answer: 'answer',
    sources: ['dailymed-warfarin.md'],
    citations: [
      {
        id: 'S1',
        source_file: 'dailymed-warfarin.md',
        section: '4 CONTRAINDICATIONS',
        chunk_id: 'c0',
        excerpt: 'warfarin contraindicated in pregnancy',
      },
    ],
    disclaimer: '',
    tool_calls: [{ tool: 'label_section_lookup', arguments: { drug: 'warfarin' }, status: 'ok' }],
    review: { verdict: 'pass', unsupported_claims: [], ambiguity_flags: [] },
    retrieval_mode: 'hybrid',
    retrieval: {
      mode: 'hybrid',
      candidates: 10,
      returned: 3,
      chunks: [
        {
          chunk_id: 'c0',
          source_file: 'dailymed-warfarin.md',
          section_path: '4 CONTRAINDICATIONS',
          excerpt: 'warfarin contraindicated in pregnancy',
          dense_rank: 1,
          bm25_rank: 2,
          fused_score: 0.03,
          cited: true,
        },
      ],
    },
    trace: [
      { stage: 'plan', status: 'done', duration_ms: 120, summary: 'simple' },
      { stage: 'retrieve', status: 'done', duration_ms: 80, summary: '1 chunk' },
    ],
    trace_id: 't1',
    usage: { tokens_in: 10, tokens_out: 20 },
    latency_ms: 250,
  }
}

function makeTurn(): Turn {
  return {
    id: 'turn-1',
    question: 'q?',
    createdAt: Date.now(),
    status: 'done',
    response: makeResponse(),
  }
}

describe('TracePanel', () => {
  it('shows the index status from /health', async () => {
    render(<TracePanel turn={null} />)
    expect(await screen.findByText('Index ready')).toBeInTheDocument()
  })

  it('lists retrieved chunks with ranks and the cited S-number', async () => {
    render(<TracePanel turn={makeTurn()} />)
    expect(await screen.findByTestId('trace-chunks')).toBeInTheDocument()
    expect(screen.getByTestId('trace-chunk-0')).toHaveTextContent('dailymed-warfarin.md')
    expect(screen.getByTestId('trace-chunk-0')).toHaveTextContent(/dense 1/)
    expect(screen.getByTestId('trace-chunk-0')).toHaveTextContent('S1')
  })

  it('shows metrics, tool calls and the review verdict', async () => {
    render(<TracePanel turn={makeTurn()} />)
    expect(await screen.findByTestId('trace-metrics')).toBeInTheDocument()
    expect(screen.getByTestId('trace-tools')).toHaveTextContent('label_section_lookup')
    expect(screen.getByTestId('trace-review')).toHaveTextContent('pass')
  })
})
