import { useState, type KeyboardEvent } from 'react'
import { Lock, Pencil, Plus, Trash2 } from 'lucide-react'

import { useHistoryStore } from '../stores/history'
import type { Session } from '../types/ui'

type GroupLabel = 'Today' | 'Yesterday' | 'Earlier'

const DAY_MS = 86_400_000

function groupLabel(createdAt: number): GroupLabel {
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  if (createdAt >= startOfToday) return 'Today'
  if (createdAt >= startOfToday - DAY_MS) return 'Yesterday'
  return 'Earlier'
}

/** Sessions persist in this browser (decision 8: never claim local-only LLM). */
export function HistorySidebar() {
  const sessions = useHistoryStore((state) => state.sessions)
  const activeSessionId = useHistoryStore((state) => state.activeSessionId)
  const newSession = useHistoryStore((state) => state.newSession)
  const selectSession = useHistoryStore((state) => state.selectSession)
  const renameSession = useHistoryStore((state) => state.renameSession)
  const deleteSession = useHistoryStore((state) => state.deleteSession)
  const clearAll = useHistoryStore((state) => state.clearAll)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [draftTitle, setDraftTitle] = useState('')

  const startRename = (session: Session) => {
    setEditingId(session.id)
    setDraftTitle(session.title)
  }

  const commitRename = () => {
    if (editingId) renameSession(editingId, draftTitle)
    setEditingId(null)
  }

  const cancelRename = () => setEditingId(null)

  const handleRenameKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      commitRename()
    } else if (event.key === 'Escape') {
      event.preventDefault()
      cancelRename()
    }
  }

  const confirmDelete = (session: Session) => {
    if (window.confirm(`Delete "${session.title}"? This cannot be undone.`)) {
      deleteSession(session.id)
    }
  }

  const confirmClearAll = () => {
    if (window.confirm('Clear all history? This cannot be undone.')) {
      clearAll()
    }
  }

  const groups: Array<{ label: GroupLabel; sessions: Session[] }> = []
  for (const session of sessions) {
    const label = groupLabel(session.createdAt)
    const existing = groups.find((group) => group.label === label)
    if (existing) existing.sessions.push(session)
    else groups.push({ label, sessions: [session] })
  }

  return (
    <div data-testid="history-sidebar" className="flex h-full flex-col gap-2 p-3">
      <button
        type="button"
        data-testid="history-new-session"
        onClick={() => newSession()}
        className="flex items-center justify-center gap-2 rounded-lg border border-line px-3 py-2 text-sm font-medium text-ink transition-colors hover:bg-accent-soft"
      >
        <Plus className="h-4 w-4" aria-hidden="true" />
        New question
      </button>

      {sessions.length === 0 ? (
        <p className="px-1 py-2 text-xs text-ink-muted">
          No history yet. Your sessions stay in this browser.
        </p>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto">
          {groups.map((group) => (
            <div key={group.label} className="mt-2">
              <h3 className="px-2 text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                {group.label}
              </h3>
              <ul className="mt-1 space-y-0.5">
                {group.sessions.map((session) => (
                  <li
                    key={session.id}
                    data-testid={`history-session-${session.id}`}
                    className={`group flex items-center gap-1 rounded-lg border-l-2 ${
                      session.id === activeSessionId
                        ? 'border-accent bg-glacial/20'
                        : 'border-transparent hover:bg-glacial/10'
                    }`}
                  >
                    {editingId === session.id ? (
                      <input
                        data-testid="history-rename-input"
                        autoFocus
                        aria-label="Rename session"
                        value={draftTitle}
                        onChange={(event) => setDraftTitle(event.target.value)}
                        onKeyDown={handleRenameKeyDown}
                        onBlur={cancelRename}
                        className="min-w-0 flex-1 bg-transparent px-2 py-2 text-sm text-ink focus:outline-none"
                      />
                    ) : (
                      <button
                        type="button"
                        data-testid={`history-session-button-${session.id}`}
                        onClick={() => selectSession(session.id)}
                        className="min-w-0 flex-1 truncate px-2 py-2 text-left text-sm text-ink"
                      >
                        {session.title}
                      </button>
                    )}
                    {editingId !== session.id && (
                      <span className="flex opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
                        <button
                          type="button"
                          data-testid={`history-rename-${session.id}`}
                          aria-label="Rename session"
                          onClick={() => startRename(session)}
                          className="rounded p-1 text-ink-muted hover:text-ink"
                        >
                          <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          data-testid={`history-delete-${session.id}`}
                          aria-label="Delete session"
                          onClick={() => confirmDelete(session)}
                          className="rounded p-1 text-ink-muted hover:text-ink"
                        >
                          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                        </button>
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <button
            type="button"
            data-testid="history-clear-all"
            onClick={confirmClearAll}
            className="mt-3 w-full rounded-lg px-2 py-2 text-left text-xs text-ink-muted transition-colors hover:bg-glacial/10"
          >
            Clear all history
          </button>
        </div>
      )}

      <p className="mt-auto flex items-center gap-1.5 border-t border-line px-1 pt-2 text-[11px] text-ink-muted">
        <Lock className="h-3 w-3" aria-hidden="true" />
        History stays in this browser
      </p>
    </div>
  )
}
