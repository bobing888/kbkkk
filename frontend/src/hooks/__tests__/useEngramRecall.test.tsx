import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { useEngramRecall } from '../useEngramRecall'
import type { EngramChunk } from '../../types/engram'

// Mock VITE_API_BASE（实际值不重要）
vi.stubEnv('VITE_API_BASE', 'http://localhost:8000')

const MOCK_CHUNKS: EngramChunk[] = [
  { id: '1', text: 'KDJ 金叉死叉有 4 场景', score: 0.92, source: 'a.md', lines: [1, 5], when: '2026-10-01T00:00:00Z', citation: 'a.md:1-5' },
  { id: '2', text: 'MACD 背离识别', score: 0.85, source: 'b.md', lines: [10, 20], when: '2026-10-02T00:00:00Z', citation: 'b.md:10-20' },
]

/** 包裹器：提供新 QueryClient 避免缓存复用 */
function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('useEngramRecall', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  test('初始状态：isLoading=true，data=[]，error=null', () => {
    // fetch 永远 pending（不 resolve）以保持 loading
    vi.spyOn(global, 'fetch').mockImplementation(
      () => new Promise<Response>(() => {})
    )
    const { result } = renderHook(() => useEngramRecall('KDJ'), { wrapper })
    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toEqual([])
    expect(result.current.error).toBe(null)
  })

  test('成功：data 返回 engram chunk 列表', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ chunks: MOCK_CHUNKS }),
    } as Response)
    const { result } = renderHook(() => useEngramRecall('KDJ'), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data).toEqual(MOCK_CHUNKS)
    expect(result.current.error).toBe(null)
  })

  test('失败：error 返回 Error 实例', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ error: 'internal' }),
    } as Response)
    const { result } = renderHook(() => useEngramRecall('KDJ'), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.error).toBeInstanceOf(Error)
  })

  test('空 query 不发请求', () => {
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ chunks: [] }),
    } as Response)
    const { result } = renderHook(() => useEngramRecall(''), { wrapper })
    expect(result.current.isLoading).toBe(false)
    expect(result.current.data).toEqual([])
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  test('空 chunks 数组返回 data=[]', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ chunks: [] }),
    } as Response)
    const { result } = renderHook(() => useEngramRecall('无结果'), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data).toEqual([])
    expect(result.current.error).toBe(null)
  })

  test('isFetching 在加载中为 true', () => {
    vi.spyOn(global, 'fetch').mockImplementation(
      () => new Promise<Response>(() => {})
    )
    const { result } = renderHook(() => useEngramRecall('KDJ'), { wrapper })
    expect(result.current.isFetching).toBe(true)
  })
})
