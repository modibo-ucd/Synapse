import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Footer } from './Footer'

vi.mock('../lib/api/client', () => ({
  getHealth: vi.fn(async () => ({
    status: 'ok',
    index: 'ready',
    llm_configured: true,
    version: '0.2.0',
    index_stats: null,
  })),
}))

describe('Footer', () => {
  it('shows the status, the version badge and the privacy note', async () => {
    render(<Footer />)
    expect(await screen.findByText('Index ready')).toBeInTheDocument()
    expect(screen.getByTestId('footer-version')).toHaveTextContent('v0.2.0')
    expect(screen.getByTestId('footer-history-note')).toHaveTextContent(
      'History stays in this browser',
    )
  })

  it('links the version badge to the docs', async () => {
    render(<Footer />)
    const link = await screen.findByTestId('footer-version')
    expect(link).toHaveAttribute('href', '/docs')
  })
})
