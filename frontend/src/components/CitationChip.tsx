import { useRef, useState } from 'react'

import type { Citation } from '../types/api'

interface CitationChipProps {
  id: string
  citation: Citation | undefined
}

function scrollToSource(id: string) {
  const target = document.getElementById(`cite-source-${id}`)
  target?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  target?.classList.add('citation-highlight')
  window.setTimeout(() => target?.classList.remove('citation-highlight'), 2500)
}

export function CitationChip({ id, citation }: CitationChipProps) {
  const [open, setOpen] = useState(false)
  const closeTimer = useRef<number | null>(null)

  if (!citation) {
    return <span className="text-slate-500">{`[${id}]`}</span>
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

  const handleClick = () => {
    scrollToSource(id)
    setOpen(true)
  }

  const handleViewInSources = () => {
    scrollToSource(id)
    setOpen(false)
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
        onClick={handleClick}
        className="mx-0.5 rounded bg-brand-50 px-1 align-super text-xs font-medium text-brand-700 hover:bg-brand-100 focus:outline-none focus:ring-2 focus:ring-brand-500/40"
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
          className="absolute bottom-full left-0 z-20 mb-2 w-72 rounded-md border border-slate-200 bg-white p-3 text-left shadow-lg"
        >
          <p className="text-xs font-semibold text-slate-700">{citation.source_file}</p>
          {citation.section && <p className="text-xs text-slate-500">{citation.section}</p>}
          <p className="mt-1 text-xs leading-relaxed text-slate-600">{citation.excerpt}</p>
          <button
            type="button"
            onClick={handleViewInSources}
            className="mt-2 text-xs font-medium text-brand-600 hover:underline focus:outline-none focus:ring-2 focus:ring-brand-500/40"
          >
            View in Sources
          </button>
        </span>
      )}
    </span>
  )
}
