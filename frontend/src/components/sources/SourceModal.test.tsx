import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useSourceDocument } from '../../hooks/useSourceDocument'
import type { SourceDocument } from '../../types/api'
import type { SourceViewTarget } from '../../types/ui'
import { SourceModal } from './SourceModal'

vi.mock('../../hooks/useSourceDocument', () => ({
  useSourceDocument: vi.fn(),
}))

const mockedHook = vi.mocked(useSourceDocument)

const sourceDoc: SourceDocument = {
  file_name: 'dailymed-warfarin.md',
  title: 'Warfarin (DailyMed label)',
  drug_name: 'warfarin',
  source_type: 'dailymed',
  markdown: '# Warfarin\n\nFirst cited passage.\n\nOther passage.',
  chunks: [{ chunk_id: 'c1', section_path: '4 CONTRAINDICATIONS', start: 11, end: 30 }],
}

const target: SourceViewTarget = {
  fileName: 'dailymed-warfarin.md',
  primaryChunkIds: ['c1'],
  secondaryChunkIds: [],
}

function readyState() {
  return { status: 'ready' as const, document: sourceDoc, error: null, retry: vi.fn() }
}

describe('SourceModal', () => {
  beforeEach(() => {
    mockedHook.mockReset()
  })

  it('opens and highlights the primary passage', async () => {
    mockedHook.mockReturnValue(readyState())
    const { container } = render(<SourceModal target={target} onClose={() => {}} />)
    expect(screen.getByTestId('source-modal')).toHaveAttribute('open')
    await screen.findByText('First cited passage.')
    expect(container.querySelector('[data-highlight="primary"]')).not.toBeNull()
  })

  it('scrolls the first primary passage into view', async () => {
    mockedHook.mockReturnValue(readyState())
    const spy = vi.spyOn(Element.prototype, 'scrollIntoView')
    render(<SourceModal target={target} onClose={() => {}} />)
    await screen.findByText('First cited passage.')
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })

  it('closes on Escape and restores focus to the opener', async () => {
    mockedHook.mockReturnValue(readyState())
    const onClose = vi.fn()
    const { rerender } = render(
      <>
        <button type="button" data-testid="opener">
          open
        </button>
        <SourceModal target={null} onClose={onClose} />
      </>,
    )
    const opener = screen.getByTestId('opener')
    opener.focus()
    rerender(
      <>
        <button type="button" data-testid="opener">
          open
        </button>
        <SourceModal target={target} onClose={onClose} />
      </>,
    )
    await screen.findByText('First cited passage.')
    fireEvent.keyDown(screen.getByTestId('source-modal'), { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
    expect(document.activeElement).toBe(opener)
  })

  it('shows the error state with a Retry button', () => {
    mockedHook.mockReturnValue({
      status: 'error',
      document: null,
      error: 'Unknown source file.',
      retry: vi.fn(),
    })
    render(<SourceModal target={target} onClose={() => {}} />)
    expect(screen.getByTestId('source-modal-error')).toBeInTheDocument()
    expect(screen.getByText('Unknown source file.')).toBeInTheDocument()
    expect(screen.getByTestId('source-modal-retry')).toBeInTheDocument()
  })
})
