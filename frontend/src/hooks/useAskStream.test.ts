import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useAskStream } from './useAskStream'

const validBody = {
  answer: 'Answer text.',
  sources: ['dailymed-warfarin.md'],
  citations: [],
  disclaimer: 'Not medical advice.',
  tool_calls: [],
  review: { verdict: 'pass', unsupported_claims: [], ambiguity_flags: [] },
  retrieval_mode: 'hybrid',
  trace_id: 't1',
  usage: { tokens_in: 10, tokens_out: 20 },
  latency_ms: 100,
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useAskStream', () => {
  it('falls back to /ask exactly once when /ask/stream fails', async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url === '/ask/stream') {
        return {
          ok: false,
          status: 404,
          json: async () => ({ error: { code: 'not_found', message: 'nope' } }),
        } as unknown as Response
      }
      return { ok: true, status: 200, json: async () => validBody } as unknown as Response
    })
    vi.stubGlobal('fetch', fetchMock as unknown as typeof fetch)

    const { result } = renderHook(() => useAskStream())
    const onStage = vi.fn()
    const onResult = vi.fn()
    const onError = vi.fn()
    await act(async () => {
      await result.current.start('q', { onStage, onResult, onError })
    })
    expect(onResult).toHaveBeenCalledTimes(1)
    expect(onError).not.toHaveBeenCalled()
    expect(onStage).not.toHaveBeenCalled()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('maps a user abort to an aborted ApiError without falling back', async () => {
    const fetchMock = vi.fn(async () => {
      throw new DOMException('Aborted', 'AbortError')
    })
    vi.stubGlobal('fetch', fetchMock as unknown as typeof fetch)

    const { result } = renderHook(() => useAskStream())
    const onError = vi.fn()
    await act(async () => {
      await result.current.start('q', { onStage: vi.fn(), onResult: vi.fn(), onError })
    })
    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'aborted' }))
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('surfaces the /ask error when the fallback also fails', async () => {
    const fetchMock = vi.fn(async () => {
      return {
        ok: false,
        status: 503,
        json: async () => ({ error: { code: 'provider_error', message: 'LLM down' } }),
      } as unknown as Response
    })
    vi.stubGlobal('fetch', fetchMock as unknown as typeof fetch)

    const { result } = renderHook(() => useAskStream())
    const onError = vi.fn()
    await act(async () => {
      await result.current.start('q', { onStage: vi.fn(), onResult: vi.fn(), onError })
    })
    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'provider_error' }))
  })
})
