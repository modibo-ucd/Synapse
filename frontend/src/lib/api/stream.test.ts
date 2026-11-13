import { afterEach, describe, expect, it, vi } from 'vitest'

import { SSEParser, streamAsk } from './stream'

const encoder = new TextEncoder()

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

function stageEvent(stage: string): string {
  const payload = { stage, status: 'ok', duration_ms: 10, summary: 'ok' }
  return `event: stage\ndata: ${JSON.stringify(payload)}\n\n`
}

function resultEvent(): string {
  return `event: result\ndata: ${JSON.stringify(validBody)}\n\n`
}

function streamBody(chunks: string[]) {
  let index = 0
  return {
    getReader: () => ({
      read: async () =>
        index < chunks.length
          ? { done: false, value: encoder.encode(chunks[index++] ?? '') }
          : { done: true, value: undefined },
      cancel: async () => {},
    }),
  }
}

function mockStreamFetch(chunks: string[]) {
  const fetchMock = vi.fn(
    async () =>
      ({
        ok: true,
        status: 200,
        body: streamBody(chunks),
      }) as unknown as Response,
  )
  vi.stubGlobal('fetch', fetchMock as unknown as typeof fetch)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('SSEParser', () => {
  it('parses a complete stream split across arbitrary chunks', () => {
    const parser = new SSEParser()
    const bytes = encoder.encode(stageEvent('plan') + resultEvent())
    const events = [
      ...parser.push(bytes.slice(0, 3)),
      ...parser.push(bytes.slice(3, 20)),
      ...parser.push(bytes.slice(20)),
    ]
    expect(events.map((event) => event.type)).toEqual(['stage', 'result'])
    expect(events[0]).toMatchObject({ type: 'stage', data: { stage: 'plan', status: 'done' } })
  })

  it('decodes a multi-byte character split across chunk boundaries', () => {
    const parser = new SSEParser()
    const message = `event: stage\ndata: ${JSON.stringify({ stage: 'plan', status: 'ok', duration_ms: 1, summary: '…' })}\n\n`
    const bytes = encoder.encode(message)
    const index = bytes.indexOf(0xe2) // first byte of the UTF-8 ellipsis
    const events = [
      ...parser.push(bytes.slice(0, index + 1)),
      ...parser.push(bytes.slice(index + 1)),
    ]
    expect(events).toHaveLength(1)
    expect(events[0]).toMatchObject({ type: 'stage', data: { summary: '…' } })
  })

  it('ignores comment lines', () => {
    const parser = new SSEParser()
    const message = `: keep-alive\nevent: stage\ndata: ${JSON.stringify({ stage: 'plan', status: 'ok', duration_ms: 1, summary: 'ok' })}\n\n`
    const events = parser.push(encoder.encode(message))
    expect(events).toHaveLength(1)
    expect(events[0]).toMatchObject({ type: 'stage' })
  })

  it('skips malformed JSON data', () => {
    const parser = new SSEParser()
    const events = parser.push(encoder.encode('event: stage\ndata: {not valid json}\n\n'))
    expect(events).toHaveLength(0)
  })

  it('joins multi-line data fields into one payload', () => {
    const parser = new SSEParser()
    const message =
      'event: stage\ndata: {"stage":"plan","status":"ok","duration_ms":1,\ndata: "summary":"ok"}\n\n'
    const events = parser.push(encoder.encode(message))
    expect(events).toHaveLength(1)
    expect(events[0]).toMatchObject({ type: 'stage', data: { stage: 'plan', summary: 'ok' } })
  })

  it('routes an error event with its payload', () => {
    const parser = new SSEParser()
    const message = 'event: error\ndata: {"error":{"code":"provider_error","message":"boom"}}\n\n'
    const events = parser.push(encoder.encode(message))
    expect(events).toHaveLength(1)
    expect(events[0]).toMatchObject({
      type: 'error',
      data: { code: 'provider_error', message: 'boom' },
    })
  })
})

describe('streamAsk', () => {
  it('emits stage events and resolves with the result', async () => {
    mockStreamFetch([stageEvent('plan'), stageEvent('retrieve'), resultEvent()])
    const onStage = vi.fn()
    const result = await streamAsk('q', onStage)
    expect(onStage).toHaveBeenCalledTimes(2)
    expect(onStage.mock.calls[0]?.[0]).toMatchObject({ stage: 'plan', status: 'done' })
    expect(result.answer).toBe('Answer text.')
  })

  it('throws the server error event as an ApiError', async () => {
    mockStreamFetch([
      'event: error\ndata: {"error":{"code":"provider_error","message":"boom"}}\n\n',
    ])
    await expect(streamAsk('q', vi.fn())).rejects.toMatchObject({
      code: 'provider_error',
      message: 'boom',
    })
  })

  it('throws when the stream ends without a result', async () => {
    mockStreamFetch([stageEvent('plan')])
    await expect(streamAsk('q', vi.fn())).rejects.toMatchObject({ code: 'invalid_response' })
  })

  it('maps a non-ok response to an ApiError', async () => {
    const fetchMock = vi.fn(
      async () =>
        ({
          ok: false,
          status: 404,
          json: async () => ({ error: { code: 'not_found', message: 'nope' } }),
        }) as unknown as Response,
    )
    vi.stubGlobal('fetch', fetchMock as unknown as typeof fetch)
    await expect(streamAsk('q', vi.fn())).rejects.toMatchObject({ code: 'not_found' })
  })
})
