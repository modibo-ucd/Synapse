import { useRef, useState } from 'react'

import type { Citation } from '../types/api'

interface CitationChipProps {
  id: string
  citation: Citation | undefined
  onOpen?: (citation: Citation) => void
}

/**
 * Inline citation chip. Hover/focus shows an excerpt tooltip; click opens the
 * source modal at this citation's chunk. Unknown ids render as plain text.
 */
export function CitationChip({ id, citation, onOpen }: CitationChipProps) {
  const [open, setOpen] = useState(false)
  const closeTimer = useRef<number | null>(null)

  if (!citation) {
    return <span className="text-ink-muted">{`[${id}]`}</span>
  }

  const clearCloseTimer = () => {
    if (closeTimer.current !== null) {
      window.clearTimeout(closeTimer.current)
      closeTimer.current = null
    }
  }

  const openPopover = () => {
    clearCloseTimer()
    setOpen(true)
  }

  const scheduleClose = () => {
    closeTimer.current = window.setTimeout(() => setOpen(false), 150)
  }

  return (
    <span className="relative inline-block">
      <button
        type="button"
        data-testid={`citation-${id}`}
        aria-label={`Citation ${id}`}
        aria-expanded={open}
        aria-describedby={open ? `citation-popover-${id}` : undefined}
        onMouseEnter={openPopover}
        onMouseLeave={scheduleClose}
        onFocus={openPopover}
        onBlur={scheduleClose}
        onClick={() => onOpen?.(citation)}
        className="mx-0.5 rounded bg-accent-soft px-1 align-super text-xs font-medium text-accent focus:outline-none"
      >
        {id}
      </button>
      {open && (
        <span
          id={`citation-popover-${id}`}
          role="tooltip"
          data-testid={`citation-popover-${id}`}
          onMouseEnter={clearCloseTimer}
          onMouseLeave={scheduleClose}
          className="absolute bottom-full left-0 z-20 mb-2 w-72 rounded-lg border border-line bg-surface p-3 text-left shadow-float"
        >
          <p className="text-xs font-semibold text-ink">{citation.source_file}</p>
          {citation.section && <p className="text-xs text-ink-muted">{citation.section}</p>}
          <p className="mt-1 text-xs leading-relaxed text-ink-muted">{citation.excerpt}</p>
        </span>
      )}
    </span>
  )
}
