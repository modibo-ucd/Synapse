import { useRef } from 'react'

import { useAutoScroll } from '../../hooks/useAutoScroll'
import type { Turn } from '../../types/ui'
import { AnswerCard } from './AnswerCard'
import { EmptyState } from './EmptyState'
import { UserBubble } from './UserBubble'

interface ChatFeedProps {
  turns: Turn[]
  onSelectExample: (question: string) => void
}

/** Scroll region with one UserBubble + AnswerCard per turn; EmptyState when empty. */
export function ChatFeed({ turns, onSelectExample }: ChatFeedProps) {
  const scrollerRef = useRef<HTMLDivElement>(null)
  const lastStatus = turns[turns.length - 1]?.status
  useAutoScroll(scrollerRef, [turns.length, lastStatus])

  return (
    <div
      ref={scrollerRef}
      data-testid="chat-feed"
      className="min-h-0 flex-1 scroll-pb-24 overflow-y-auto"
    >
      <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
        {turns.length === 0 ? (
          <EmptyState onSelect={onSelectExample} />
        ) : (
          turns.map((turn) => (
            <div key={turn.id} className="space-y-4">
              <UserBubble text={turn.question} />
              <AnswerCard turn={turn} scrollerRef={scrollerRef} />
            </div>
          ))
        )}
      </div>
    </div>
  )
}
