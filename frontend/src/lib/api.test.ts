import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, askQuestion, getHealth } from './api/client'

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

  it('maps a network failure to a network_error ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('fetch failed')
      }),
    )
    await expect(askQuestion('x')).rejects.toMatchObject({ code: 'network_error' })
  })

  it('maps a cancelled request to an aborted ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new DOMException('Aborted', 'AbortError')
      }),
    )
    const controller = new AbortController()
    controller.abort()
    await expect(askQuestion('x', controller.signal)).rejects.toMatchObject({ code: 'aborted' })
  })
})

describe('getHealth', () => {
  it('parses a successful health response', async () => {
    mockFetch(200, {
      status: 'ok',
      index: 'ready',
      llm_configured: true,
      version: '0.1.0',
      index_stats: { files: 21, chunks: 300, embedding_model: 'text-embedding-3-small' },
    })
    const health = await getHealth()
    expect(health.index).toBe('ready')
    expect(health.index_stats?.files).toBe(21)
  })

  it('maps a non-ok health response to an ApiError', async () => {
    mockFetch(500, { error: { code: 'internal_error', message: 'boom' } })
    await expect(getHealth()).rejects.toMatchObject({ code: 'internal_error' })
  })
})
