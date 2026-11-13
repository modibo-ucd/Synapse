import { useEffect, useRef, type KeyboardEvent } from 'react'

import { haptic } from '../../lib/haptics'
import { useSettingsStore } from '../../stores/settings'

const MAX_LENGTH = 2000
const SHOW_COUNTER_AT = 1800
const MAX_ROWS = 6
const ROW_HEIGHT_PX = 24

interface StickyAskBarProps {
  value: string
  onChange: (value: string) => void
  onSubmit: (question: string) => void
  onStop: () => void
  pending: boolean
  disabledReason?: string | null
}

/** Composer pinned below the feed (6.7): auto-grow, IME-safe Enter, counter, Stop. */
export function StickyAskBar({
  value,
  onChange,
  onSubmit,
  onStop,
  pending,
  disabledReason,
}: StickyAskBarProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const composingRef = useRef(false)
  const haptics = useSettingsStore((state) => state.haptics)
  const disabled = Boolean(disabledReason)

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, MAX_ROWS * ROW_HEIGHT_PX)}px`
  }, [value])

  const submit = () => {
    const question = value.trim()
    if (!question || pending || disabled) return
    haptic(haptics)
    onSubmit(question)
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !composingRef.current) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="composer-pad border-t border-line bg-app px-4 pt-3">
      <div className="mx-auto max-w-3xl">
        <div className="rounded-2xl border border-line bg-surface p-2 shadow-float">
          <textarea
            ref={textareaRef}
            data-testid="question-input"
            aria-label="Ask a pharmacology question"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => {
              composingRef.current = true
            }}
            onCompositionEnd={() => {
              composingRef.current = false
            }}
            disabled={pending || disabled}
            rows={1}
            maxLength={MAX_LENGTH}
            placeholder="Ask about a drug, an interaction, or a threshold…"
            className="max-h-40 w-full resize-none bg-transparent px-2 py-2 text-sm text-ink placeholder:text-ink-muted focus:outline-none disabled:opacity-60"
          />
          <div className="flex items-center justify-between gap-2 px-1 pb-1">
            <span data-testid="ask-bar-hint" className="text-xs text-ink-muted">
              {value.length >= SHOW_COUNTER_AT
                ? `${value.length}/${MAX_LENGTH}`
                : 'Enter to send · Shift+Enter for a new line'}
            </span>
            {pending ? (
              <button
                type="button"
                data-testid="stop-button"
                onClick={onStop}
                className="rounded-xl bg-surface px-4 py-2 text-sm font-medium text-ink ring-1 ring-inset ring-line hover:bg-accent-soft"
              >
                Stop
              </button>
            ) : (
              <button
                type="button"
                data-testid="submit-button"
                onClick={submit}
                disabled={disabled || value.trim().length === 0}
                className="rounded-xl bg-action px-4 py-2 text-sm font-medium text-action-ink hover:bg-action-hover disabled:opacity-50"
              >
                Ask
              </button>
            )}
          </div>
        </div>
        <p data-testid="ask-bar-caption" className="mt-2 text-center text-xs text-ink-muted">
          Educational research tool. Not medical advice.
        </p>
        {disabledReason && (
          <p
            data-testid="ask-bar-disabled-reason"
            className="mt-1 text-center text-xs font-medium text-accent"
          >
            {disabledReason}
          </p>
        )}
      </div>
    </div>
  )
}
