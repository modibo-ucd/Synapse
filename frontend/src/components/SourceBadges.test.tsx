import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import { useUiStore } from '../stores/ui'
import type { Citation, RetrievedChunk } from '../types/api'
import { SourceBadges } from './SourceBadges'

const citations: Citation[] = [
  {
    id: 'S1',
    source_file: 'dailymed-warfarin.md',
    section: '4 CONTRAINDICATIONS',
    chunk_id: 'c1',
    excerpt: 'excerpt',
  },
]

const chunks: RetrievedChunk[] = [
  {
    chunk_id: 'c1',
    source_file: 'dailymed-warfarin.md',
    section_path: '4 CONTRAINDICATIONS',
    excerpt: 'excerpt',
    dense_rank: 1,
    bm25_rank: 2,
    fused_score: 0.03,
    cited: true,
  },
  {
    chunk_id: 'c2',
    source_file: 'dailymed-warfarin.md',
    section_path: '5 WARNINGS AND PRECAUTIONS',
    excerpt: 'other',
    dense_rank: 2,
    bm25_rank: 3,
    fused_score: 0.02,
    cited: false,
  },
]

describe('SourceBadges', () => {
  beforeEach(() => {
    useUiStore.setState({ sourceView: null })
  })

  it('renders a badge per source with a type label', () => {
    render(<SourceBadges sources={['dailymed-warfarin.md']} citations={citations} retrievedChunks={chunks} />)
    expect(
      screen.getByRole('button', { name: 'Open source dailymed-warfarin.md' }),
    ).toBeInTheDocument()
    expect(screen.getByText('DailyMed')).toBeInTheDocument()
  })

  it('opens a source view with cited and retrieved chunk ids on click', async () => {
    render(<SourceBadges sources={['dailymed-warfarin.md']} citations={citations} retrievedChunks={chunks} />)
    await userEvent.click(screen.getByRole('button', { name: 'Open source dailymed-warfarin.md' }))
    expect(useUiStore.getState().sourceView).toEqual({
      fileName: 'dailymed-warfarin.md',
      primaryChunkIds: ['c1'],
      secondaryChunkIds: ['c2'],
    })
  })
})
