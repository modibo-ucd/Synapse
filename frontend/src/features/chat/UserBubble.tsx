interface UserBubbleProps {
  text: string
}

export function UserBubble({ text }: UserBubbleProps) {
  return (
    <div className="flex justify-end">
      <div
        data-testid="user-bubble"
        className="max-w-[80%] rounded-2xl rounded-br-md bg-bubble px-4 py-3 text-sm text-ink"
      >
        {text}
      </div>
    </div>
  )
}
