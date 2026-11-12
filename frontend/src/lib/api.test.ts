import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, askQuestion } from './api'

const validBody = {
  answer: 'Answer text.',
  sources: ['dailymed-warfarin.md'],
  citations: [
    {
      id: 'S1',
      source_file: 'dailymed-warfarin.md',
      section: 'Contraindications',
      chunk_id: 'c1',
      excerpt: 'excerpt',
    },
  ],
  disclaimer: 'Not medical advice.',
  plan: { complexity: 'simple', in_scope: true, sub_goals: [] },
  tool_calls: [],
  review: { verdict: 'pass', unsupported_claims: [], ambiguity_flags: [] },
  retrieval_mode: 'hybrid',
  trace_id: 't1',
  usage: { tokens_in: 10, tokens_out: 20 },
  latency_ms: 123.4,
}

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }))
  vi.stubGlobal('fetch', fetchMock as unknown as typeof fetch)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('askQuestion', () => {
  it('parses a successful response', async () => {
    mockFetch(200, validBody)
    const result = await askQuestion('warfarin?')
    expect(result.answer).toBe('Answer text.')
    expect(result.citations[0]?.source_file).toBe('dailymed-warfarin.md')
  })

  it('maps an error body to a typed ApiError', async () => {
    mockFetch(503, {
      error: { code: 'configuration_error', message: 'LLM not configured.', request_id: 'abc' },
    })
    await expect(askQuestion('x')).rejects.toMatchObject({
      name: 'ApiError',
      code: 'configuration_error',
      message: 'LLM not configured.',
      requestId: 'abc',
    })
  })

  it('rejects with an ApiError on an invalid response shape', async () => {
    mockFetch(200, { unexpected: true })
    await expect(askQuestion('x')).rejects.toBeInstanceOf(ApiError)
  })
})
