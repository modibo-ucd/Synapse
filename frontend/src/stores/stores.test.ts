import { beforeEach, describe, expect, it, vi } from 'vitest'

import { safeStorage } from '../lib/storage/safeStorage'
import { useSettingsStore } from './settings'
import { useUiStore } from './ui'
import { compactForStorage, deriveTitle, useHistoryStore } from './history'
import type { AskResponse } from '../types/api'

function resetStores() {
  useHistoryStore.setState({ sessions: [], activeSessionId: null })
  useSettingsStore.setState({ theme: 'system', haptics: true, historyOpen: true, traceOpen: true })
  useUiStore.setState({
    selectedTurnId: null,
    sourceView: null,
    zenTurnId: null,
    drawer: null,
    storageWarning: false,
  })
}

function makeResponse(): AskResponse {
  return {
    answer: 'answer',
    sources: ['dailymed-warfarin.md'],
    citations: [],
    disclaimer: '',
    tool_calls: [],
    review: { verdict: 'pass', unsupported_claims: [], ambiguity_flags: [] },
    retrieval_mode: 'hybrid',
    trace_id: 't',
    usage: { tokens_in: 1, tokens_out: 1 },
    latency_ms: 1,
    retrieval: {
      mode: 'hybrid',
      candidates: 10,
      returned: 10,
      chunks: Array.from({ length: 10 }, (_, i) => ({
        chunk_id: `c${i}`,
        source_file: 'dailymed-warfarin.md',
        section_path: '4 CONTRAINDICATIONS',
        excerpt: `excerpt ${i} `.padEnd(400, 'x'),
        dense_rank: i,
        bm25_rank: i,
        fused_score: 0,
        cited: i < 2,
      })),
    },
  }
}

describe('history store', () => {
  beforeEach(() => {
    window.localStorage.clear()
    resetStores()
  })

  it('persists with schema version 1 and partialized shape', () => {
    const options = useHistoryStore.persist.getOptions()
    expect(options.name).toBe('synapse.history')
    expect(options.version).toBe(1)
  })

  it('creates, selects, renames, deletes and clears sessions', () => {
    const store = useHistoryStore.getState()
    const first = store.newSession()
    const second = store.newSession()

    expect(useHistoryStore.getState().activeSessionId).toBe(second)
    expect(useHistoryStore.getState().sessions).toHaveLength(2)

    useHistoryStore.getState().selectSession(first)
    expect(useHistoryStore.getState().activeSessionId).toBe(first)

    useHistoryStore.getState().renameSession(first, 'Warfarin notes')
    const renamed = useHistoryStore.getState().sessions.find((s) => s.id === first)
    expect(renamed?.title).toBe('Warfarin notes')
    expect(renamed?.titleEdited).toBe(true)

    useHistoryStore.getState().deleteSession(first)
    expect(useHistoryStore.getState().sessions.map((s) => s.id)).toEqual([second])

    useHistoryStore.getState().clearAll()
    expect(useHistoryStore.getState().sessions).toHaveLength(0)
    expect(useHistoryStore.getState().activeSessionId).toBeNull()
  })

  it('derives a capped title from the first question until renamed', () => {
    const id = useHistoryStore.getState().newSession()
    useHistoryStore.getState().addTurn(id, 'Warfarin contraindications?')
    const session = useHistoryStore.getState().sessions.find((s) => s.id === id)!
    expect(session.title).toBe('Warfarin contraindications?')
    expect(session.titleEdited).toBe(false)
  })

  it('adds and updates turns', () => {
    const id = useHistoryStore.getState().newSession()
    const turn = useHistoryStore.getState().addTurn(id, 'question')
    expect(turn.status).toBe('pending')
    useHistoryStore.getState().updateTurn(id, turn.id, { status: 'done', error: 'oops' })
    const updated = useHistoryStore.getState().sessions[0]!.turns[0]!
    expect(updated.status).toBe('done')
    expect(updated.error).toBe('oops')
  })

  it('caps sessions at 50', () => {
    const store = useHistoryStore.getState()
    for (let i = 0; i < 55; i += 1) store.newSession()
    expect(useHistoryStore.getState().sessions).toHaveLength(50)
  })

  it('caps turns at 200 by evicting the oldest', () => {
    const id = useHistoryStore.getState().newSession()
    const store = useHistoryStore.getState()
    for (let i = 0; i < 205; i += 1) store.addTurn(id, `question ${i}`)
    const session = useHistoryStore.getState().sessions.find((s) => s.id === id)!
    expect(session.turns).toHaveLength(200)
    expect(session.turns[0]!.question).toBe('question 5')
  })

  it('evicts oldest sessions and warns when storage quota is exceeded', () => {
    const store = useHistoryStore.getState()
    for (let i = 0; i < 4; i += 1) store.newSession()
    const quota = new DOMException('quota', 'QuotaExceededError')
    vi.spyOn(safeStorage, 'setItem').mockImplementation(() => {
      throw quota
    })
    store.newSession()
    expect(useUiStore.getState().storageWarning).toBe(true)
    expect(useHistoryStore.getState().sessions.length).toBeLessThan(5)
    vi.restoreAllMocks()
  })
})

describe('settings store', () => {
  beforeEach(() => {
    window.localStorage.clear()
    resetStores()
  })

  it('defaults to system theme and persists changes under synapse.settings', () => {
    expect(useSettingsStore.getState().theme).toBe('system')
    useSettingsStore.getState().setTheme('dark')
    expect(useSettingsStore.getState().theme).toBe('dark')
    expect(window.localStorage.getItem('synapse.settings')).toContain('dark')
  })
})

describe('pure helpers', () => {
  it('deriveTitle normalizes whitespace and caps at 48 characters', () => {
    expect(deriveTitle('  hello   world  ')).toBe('hello world')
    expect(deriveTitle('x'.repeat(100))).toHaveLength(48)
  })

  it('compactForStorage trims excerpts and drops them beyond 8 chunks', () => {
    const compacted = compactForStorage(makeResponse())
    const chunks = compacted.retrieval!.chunks
    expect(chunks).toHaveLength(10)
    expect(chunks[0]!.excerpt).toHaveLength(300)
    expect(chunks[8]!.excerpt).toBe('')
    expect(chunks[9]!.excerpt).toBe('')
  })

  it('compactForStorage leaves small responses untouched', () => {
    const response = makeResponse()
    response.retrieval!.chunks = response.retrieval!.chunks.slice(0, 8)
    expect(compactForStorage(response)).toBe(response)
  })
})
