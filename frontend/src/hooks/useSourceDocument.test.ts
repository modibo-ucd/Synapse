import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getSourceDocument } from '../lib/api/client'
import type { SourceDocument } from '../types/api'
import { clearSourceDocumentCache, useSourceDocument } from './useSourceDocument'

vi.mock('../lib/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api/client')>()
  return { ...actual, getSourceDocument: vi.fn() }
})

const mocked = vi.mocked(getSourceDocument)

const document: SourceDocument = {
  file_name: 'dailymed-warfarin.md',
  title: 'Warfarin (DailyMed label)',
  drug_name: 'warfarin',
  source_type: 'dailymed',
  markdown: '# Warfarin\n\nContraindications.',
  chunks: [{ chunk_id: 'c1', section_path: '4', start: 0, end: 10 }],
}

describe('useSourceDocument', () => {
  beforeEach(() => {
    clearSourceDocumentCache()
    mocked.mockReset()
  })

  it('loads a document and caches it by file name', async () => {
    mocked.mockResolvedValue({ document, etag: 'W/"abc"' })
    const { result } = renderHook(() => useSourceDocument('dailymed-warfarin.md'))
    expect(result.current.status).toBe('loading')
    await waitFor(() => expect(result.current.status).toBe('ready'))
    expect(result.current.document).toEqual(document)
    expect(mocked).toHaveBeenCalledWith('dailymed-warfarin.md', undefined, expect.anything())
  })

  it('revalidates with the stored ETag on a later mount', async () => {
    mocked.mockResolvedValueOnce({ document, etag: 'W/"abc"' })
    const first = renderHook(() => useSourceDocument('dailymed-warfarin.md'))
    await waitFor(() => expect(first.result.current.status).toBe('ready'))

    mocked.mockResolvedValueOnce({ document: null, etag: 'W/"abc"' })
    const second = renderHook(() => useSourceDocument('dailymed-warfarin.md'))
    await waitFor(() => expect(second.result.current.status).toBe('ready'))
    expect(mocked).toHaveBeenLastCalledWith('dailymed-warfarin.md', 'W/"abc"', expect.anything())
    expect(second.result.current.document).toEqual(document)
  })

  it('surfaces an error and retries', async () => {
    mocked.mockRejectedValueOnce(new Error('boom'))
    const { result } = renderHook(() => useSourceDocument('missing.md'))
    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error).toBe('Could not load the source document.')

    mocked.mockResolvedValueOnce({ document, etag: 'W/"abc"' })
    act(() => result.current.retry())
    await waitFor(() => expect(result.current.status).toBe('ready'))
    expect(result.current.document).toEqual(document)
  })
})
