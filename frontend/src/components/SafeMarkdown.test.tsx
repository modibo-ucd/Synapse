import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { Citation } from '../types/api'
import { SafeMarkdown } from './SafeMarkdown'

const citation: Citation = {
  id: 'S1',
  source_file: 'dailymed-warfarin.md',
  section: '4 CONTRAINDICATIONS',
  chunk_id: 'c1',
  excerpt: 'warfarin is contraindicated in pregnancy',
}

describe('SafeMarkdown', () => {
  it('neutralizes script injection', () => {
    const { container } = render(<SafeMarkdown>{'<script>alert("xss")</script>'}</SafeMarkdown>)
    expect(container.querySelector('script')).toBeNull()
  })

  it('strips dangerous link protocols', () => {
    const { container } = render(<SafeMarkdown>{'[click](javascript:alert(1))'}</SafeMarkdown>)
    const link = container.querySelector('a')
    expect(link).not.toBeNull()
    expect(link?.getAttribute('href')).toBeNull()
  })

  it('renders markdown headings and bold text', () => {
    render(<SafeMarkdown>{'# Title\n\nA paragraph with **bold** text.'}</SafeMarkdown>)
    expect(screen.getByRole('heading', { name: 'Title' })).toBeInTheDocument()
    expect(screen.getByText('bold')).toBeInTheDocument()
  })

  it('renders GFM tables', () => {
    render(<SafeMarkdown>{'| A | B |\n| - | - |\n| 1 | 2 |'}</SafeMarkdown>)
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'A' })).toBeInTheDocument()
  })

  it('renders known citation markers as chips', () => {
    render(
      <SafeMarkdown citations={[citation]}>
        {'warfarin is contraindicated in pregnancy [S1]'}
      </SafeMarkdown>,
    )
    expect(screen.getByTestId('citation-S1')).toBeInTheDocument()
    expect(screen.queryByText('[S1]')).not.toBeInTheDocument()
  })

  it('renders unknown citation ids as plain text', () => {
    render(<SafeMarkdown citations={[]}>{'no such source [S99]'}</SafeMarkdown>)
    expect(screen.getByText('[S99]')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  describe('cross-highlighting', () => {
    it('marks the highlighted block and leaves neighbours alone', () => {
      const markdown = 'First paragraph.\n\nSecond paragraph.'
      const start = markdown.indexOf('First')
      const end = markdown.indexOf('paragraph.') + 'paragraph.'.length
      const { container } = render(
        <SafeMarkdown highlightRanges={[{ start, end, level: 'primary' }]}>
          {markdown}
        </SafeMarkdown>,
      )
      const paragraphs = container.querySelectorAll('p')
      expect(paragraphs[0]).toHaveAttribute('data-highlight', 'primary')
      expect(paragraphs[1]).not.toHaveAttribute('data-highlight')
    })

    it('marks a table row', () => {
      const markdown = '| A | B |\n| - | - |\n| 1 | 2 |\n| 3 | 4 |'
      const start = markdown.indexOf('| 1 | 2 |')
      const end = start + '| 1 | 2 |'.length
      const { container } = render(
        <SafeMarkdown highlightRanges={[{ start, end, level: 'primary' }]}>
          {markdown}
        </SafeMarkdown>,
      )
      const rows = container.querySelectorAll('tr')
      expect(rows[1]).toHaveAttribute('data-highlight', 'primary')
      expect(rows[0]).not.toHaveAttribute('data-highlight')
      expect(rows[2]).not.toHaveAttribute('data-highlight')
    })

    it('marks only the nested list item, not its parent', () => {
      const markdown = '- outer\n  - inner\n- other'
      const start = markdown.indexOf('inner')
      const end = start + 'inner'.length
      const { container } = render(
        <SafeMarkdown highlightRanges={[{ start, end, level: 'primary' }]}>
          {markdown}
        </SafeMarkdown>,
      )
      const items = container.querySelectorAll('li')
      expect(items[0]).not.toHaveAttribute('data-highlight')
      expect(items[1]).toHaveAttribute('data-highlight', 'primary')
      expect(items[2]).not.toHaveAttribute('data-highlight')
    })

    it('still strips <script> while highlighting source text', () => {
      const markdown = '<script>alert(1)</script>\n\nSafe paragraph.'
      const start = markdown.indexOf('Safe paragraph.')
      const end = start + 'Safe paragraph.'.length
      const { container } = render(
        <SafeMarkdown highlightRanges={[{ start, end, level: 'primary' }]}>
          {markdown}
        </SafeMarkdown>,
      )
      expect(container.querySelector('script')).toBeNull()
      const paragraphs = container.querySelectorAll('p')
      expect(paragraphs[0]).toHaveAttribute('data-highlight', 'primary')
    })

    it('does nothing when ranges fall outside the text', () => {
      const markdown = 'A short paragraph.'
      const { container } = render(
        <SafeMarkdown highlightRanges={[{ start: 1000, end: 2000, level: 'primary' }]}>
          {markdown}
        </SafeMarkdown>,
      )
      expect(container.querySelector('[data-highlight]')).toBeNull()
    })
  })
})
