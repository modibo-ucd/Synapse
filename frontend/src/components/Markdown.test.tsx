import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Markdown } from './Markdown'

describe('Markdown', () => {
  it('neutralizes script injection', () => {
    const { container } = render(<Markdown>{'<script>alert("xss")</script>'}</Markdown>)
    expect(container.querySelector('script')).toBeNull()
  })

  it('strips dangerous link protocols', () => {
    const { container } = render(<Markdown>{'[click me](javascript:alert("xss"))'}</Markdown>)
    const link = container.querySelector('a')
    expect(link).not.toBeNull()
    expect(link?.getAttribute('href')).toBeNull()
  })

  it('renders basic markdown', () => {
    render(<Markdown>{'# Title\n\nA paragraph with **bold** text.'}</Markdown>)
    expect(screen.getByRole('heading', { name: 'Title' })).toBeInTheDocument()
    expect(screen.getByText('bold')).toBeInTheDocument()
  })

  it('renders GFM tables', () => {
    render(<Markdown>{'| A | B |\n| - | - |\n| 1 | 2 |'}</Markdown>)
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'A' })).toBeInTheDocument()
  })

  it('turns citation markers into chips inside lists and tables', () => {
    const citations = [
      {
        id: 'S1',
        source_file: 'dailymed-warfarin.md',
        section: '4 CONTRAINDICATIONS',
        chunk_id: 'c1',
        excerpt: 'warfarin is contraindicated in pregnancy',
      },
    ]
    render(
      <Markdown citations={citations}>
        {'- warfarin is contraindicated in pregnancy [S1]\n\n| Drug | Note |\n| --- | --- |\n| warfarin | see [S1] |'}
      </Markdown>,
    )
    expect(screen.getAllByTestId('citation-S1').length).toBeGreaterThanOrEqual(2)
  })

  it('renders unknown citation ids as plain text', () => {
    const citations = [
      {
        id: 'S1',
        source_file: 'dailymed-warfarin.md',
        section: '4 CONTRAINDICATIONS',
        chunk_id: 'c1',
        excerpt: 'warfarin is contraindicated in pregnancy',
      },
    ]
    render(<Markdown citations={citations}>{'warfarin [S99]'}</Markdown>)
    expect(screen.queryByTestId('citation-S99')).not.toBeInTheDocument()
    expect(screen.getByText('[S99]')).toBeInTheDocument()
  })
})
