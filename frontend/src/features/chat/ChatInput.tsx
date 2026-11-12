import { forwardRef, type FormEvent, type KeyboardEvent } from 'react'

interface ChatInputProps {
  value: string
  disabled: boolean
  onChange: (value: string) => void
  onSubmit: (question: string) => void
}

export const ChatInput = forwardRef<HTMLTextAreaElement, ChatInputProps>(function ChatInput(
  { value, disabled, onChange, onSubmit },
  ref,
) {
  const submitQuestion = () => {
    const question = value.trim()
    if (!question || disabled) {
      return
    }
    onSubmit(question)
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    submitQuestion()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submitQuestion()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <label htmlFor="question-input" className="text-sm font-medium text-slate-700">
        Ask a pharmacology question
      </label>
      <textarea
        id="question-input"
        ref={ref}
        data-testid="question-input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        rows={3}
        maxLength={2000}
        placeholder="e.g. What are the main contraindications for warfarin?"
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/30 disabled:opacity-60"
      />
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-slate-400">Enter to send · Shift+Enter for a new line</p>
        <button
          type="submit"
          data-testid="submit-button"
          disabled={disabled || value.trim().length === 0}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500/40 disabled:opacity-50"
        >
          Ask
        </button>
      </div>
    </form>
  )
})
