import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ReadingProgress } from './ReadingProgress'

function rect(top: number, height: number): DOMRect {
  return {
    x: 0,
    y: top,
    top,
    left: 0,
    right: 0,
    bottom: top + height,
    width: 0,
    height,
    toJSON: () => ({}),
  } as DOMRect
}

class FakeResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('ReadingProgress', () => {
  it('hides when the card is not taller than the scroller', () => {
    const card = document.createElement('article')
    const scroller = document.createElement('div')
    vi.spyOn(card, 'getBoundingClientRect').mockReturnValue(rect(0, 80))
    vi.spyOn(scroller, 'getBoundingClientRect').mockReturnValue(rect(0, 100))
    render(<ReadingProgress cardRef={{ current: card }} scrollerRef={{ current: scroller }} />)
    expect(screen.queryByTestId('reading-progress')).not.toBeInTheDocument()
  })

  it('renders a bar scaled by the revealed fraction when taller', () => {
    const card = document.createElement('article')
    const scroller = document.createElement('div')
    vi.spyOn(card, 'getBoundingClientRect').mockReturnValue(rect(0, 500))
    vi.spyOn(scroller, 'getBoundingClientRect').mockReturnValue(rect(0, 100))
    render(<ReadingProgress cardRef={{ current: card }} scrollerRef={{ current: scroller }} />)
    const bar = screen.getByTestId('reading-progress')
    expect(bar).toBeInTheDocument()
    const fill = bar.firstElementChild as HTMLElement
    expect(fill.style.transform).toBe('scaleX(0.2)')
  })
})
