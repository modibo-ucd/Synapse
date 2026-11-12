import { useEffect, useRef, useState } from 'react'

import { AnswerView } from './AnswerView'
import { ChatInput } from './ChatInput'
import { ExampleQuestions } from './ExampleQuestions'
import { useChat } from './useChat'

export function ChatPage() {
  const { state, submit, reset } = useChat()
  const [inputValue, setInputValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const answerRef = useRef<HTMLDivElement>(null)
  const errorRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (state.status === 'success') {
      answerRef.current?.focus()
    } else if (state.status === 'error') {
      errorRef.current?.focus()
    }
  }, [state.status])

  const handleSubmit = (question: string) => {
    setInputValue('')
    submit(question)
  }

  const handleExampleSelect = (question: string) => {
    setInputValue(question)
    textareaRef.current?.focus()
  }

  const handleReset = () => {
    setInputValue('')
    reset()
  }

  return (
    <section className="flex flex-col gap-6">
      <ChatInput
        ref={textareaRef}
        value={inputValue}
        disabled={state.status === 'loading'}
        onChange={setInputValue}
        onSubmit={handleSubmit}
      />

      {state.status === 'loading' && (
        <div
          data-testid="loading"
          role="status"
          aria-live="polite"
          className="flex items-center gap-3 rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-600"
        >
          <span
            aria-hidden="true"
            className="h-4 w-4 animate-spin rounded-full border-2 border-brand-600 border-t-transparent"
          />
          Working… researching and verifying the answer.
        </div>
      )}

      {state.status === 'error' && (
        <div
          ref={errorRef}
          tabIndex={-1}
          data-testid="error"
          role="alert"
          className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700 focus:outline-none"
        >
          <p className="font-semibold">Something went wrong</p>
          <p>{state.error}</p>
          <button
            type="button"
            data-testid="retry-button"
            onClick={handleReset}
            className="mt-2 rounded-md border border-red-300 px-3 py-1 text-sm text-red-700 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-400/40"
          >
            Start over
          </button>
        </div>
      )}

      {state.status === 'success' && state.answer && (
        <div ref={answerRef} tabIndex={-1} className="focus:outline-none">
          <AnswerView answer={state.answer} />
        </div>
      )}

      {state.status === 'idle' && <ExampleQuestions onSelect={handleExampleSelect} />}
    </section>
  )
}
