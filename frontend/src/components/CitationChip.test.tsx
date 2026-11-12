import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { CitationChip } from './CitationChip'

const citation = {
  id: 'S1',
  source_file: 'dailymed-warfarin.md',
  section: '4 CONTRAINDICATIONS',
  chunk_id: 'c1',
  excerpt: 'warfarin is contraindicated in pregnancy',
}

describe('CitationChip', () => {
  it('opens the popover on hover', async () => {
    render(<CitationChip id="S1" citation={citation} />)
    await userEvent.hover(screen.getByTestId('citation-S1'))
    expect(await screen.findByTestId('citation-popover-S1')).toBeInTheDocument()
    expect(screen.getByText('warfarin is contraindicated in pregnancy')).toBeInTheDocument()
  })

  it('opens the popover on keyboard focus', async () => {
    render(<CitationChip id="S1" citation={citation} />)
    await userEvent.tab()
    expect(await screen.findByTestId('citation-popover-S1')).toBeInTheDocument()
  })

  it('opens the popover on tap (click)', async () => {
    render(<CitationChip id="S1" citation={citation} />)
    await userEvent.click(screen.getByTestId('citation-S1'))
    expect(await screen.findByTestId('citation-popover-S1')).toBeInTheDocument()
  })

  it('exposes an accessible name and a tooltip role', async () => {
    render(<CitationChip id="S1" citation={citation} />)
    expect(screen.getByRole('button', { name: 'Citation S1' })).toBeInTheDocument()
    await userEvent.hover(screen.getByTestId('citation-S1'))
    expect(await screen.findByRole('tooltip')).toBeInTheDocument()
    expect(screen.getByText('dailymed-warfarin.md')).toBeInTheDocument()
  })

  it('renders an unknown id as plain text', () => {
    render(<CitationChip id="S99" citation={undefined} />)
    expect(screen.getByText('[S99]')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
