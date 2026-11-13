import { useState } from 'react'

import { useHealth } from '../../hooks/useHealth'
import { ChatFeed } from './ChatFeed'
import { StickyAskBar } from './StickyAskBar'
import { useChat } from './useChat'

export function ChatPage() {
  const { turns, pending, submit, stop } = useChat()
  const [value, setValue] = useState('')
  const health = useHealth()
  const disabledReason =
    health?.status === 'unreachable'
      ? 'The API is unreachable — start the backend and try again.'
      : null

  const handleSubmit = (question: string) => {
    setValue('')
    void submit(question)
  }

  const handleSelectExample = (question: string) => {
    setValue(question)
    void submit(question)
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ChatFeed turns={turns} onSelectExample={handleSelectExample} />
      <StickyAskBar
        value={value}
        onChange={setValue}
        onSubmit={handleSubmit}
        onStop={stop}
        pending={pending}
        disabledReason={disabledReason}
      />
    </div>
  )
}
