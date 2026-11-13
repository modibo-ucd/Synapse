import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { Citation } from '../types/api'
import { CitationChip } from './CitationChip'

const citation: Citation = {
  id: 'S1',
  source_file: 'dailymed-warfarin.md',
  section: '4 CONTRAINDICATIONS',
  chunk_id: 'c1',
  excerpt: 'warfarin is contraindicated in pregnancy',
}

describe('CitationChip', () => {
  it('opens the tooltip on hover', async () => {
    render(<CitationChip id="S1" citation={citation} />)
    await userEvent.hover(screen.getByTestId('citation-S1'))
    expect(await screen.findByTestId('citation-popover-S1')).toBeInTheDocument()
  })

  it('opens the tooltip on keyboard focus', async () => {
    render(<CitationChip id="S1" citation={citation} />)
    await userEvent.tab()
    expect(await screen.findByTestId('citation-popover-S1')).toBeInTheDocument()
  })

  it('calls onOpen with the citation on click', async () => {
    const onOpen = vi.fn()
    render(<CitationChip id="S1" citation={citation} onOpen={onOpen} />)
    await userEvent.click(screen.getByTestId('citation-S1'))
    expect(onOpen).toHaveBeenCalledWith(citation)
  })

  it('exposes an accessible name and a tooltip role', async () => {
    render(<CitationChip id="S1" citation={citation} />)
    expect(screen.getByRole('button', { name: 'Citation S1' })).toBeInTheDocument()
    await userEvent.hover(screen.getByTestId('citation-S1'))
    expect(await screen.findByRole('tooltip')).toBeInTheDocument()
  })

  it('renders an unknown id as plain text', () => {
    render(<CitationChip id="S99" citation={undefined} />)
    expect(screen.getByText('[S99]')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
