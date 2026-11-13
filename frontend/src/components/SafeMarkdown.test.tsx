import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { SafeMarkdown } from './SafeMarkdown'

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

  it('renders citation markers as plain text in Phase C', () => {
    render(<SafeMarkdown>{'warfarin is contraindicated in pregnancy [S1]'}</SafeMarkdown>)
    expect(screen.getByText(/warfarin is contraindicated/)).toBeInTheDocument()
  })
})
