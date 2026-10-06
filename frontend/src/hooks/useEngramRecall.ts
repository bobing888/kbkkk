/**
 * engram recall React Hook
 * 封装 /api/v1/engram/recall，返回 { data, isLoading, error, refetch }
 *
 * 架构决策（ADR-001）：TanStack Query 包装 server proxy
 * 架构决策（ADR-002）：staleTime=60s 缓存（平衡新鲜度与性能）
 * 架构决策（ADR-003）：query 为空不请求（enabled=false）
 */
import { useQuery } from '@tanstack/react-query'
import type { EngramChunk } from '../types/engram'

const API_BASE = import.meta.env.VITE_API_BASE
const ENGRAM_ENDPOINT = `${API_BASE}/api/v1/engram/recall`

export interface UseEngramRecallOptions {
  /** 最大返回条数，默认 5 */
  limit?: number
  /** 缓存时间（ms），默认 60s */
  staleTime?: number
  /** 默认 true；传 false 强制不请求 */
  enabled?: boolean
}

/** Hook 返回值 */
export interface UseEngramRecallResult {
  data: EngramChunk[]
  isLoading: boolean
  /** 重新加载中（即使有缓存） */
  isFetching: boolean
  error: Error | null
  refetch: () => void
}

async function recallChunks(
  query: string,
  limit: number,
  signal: AbortSignal
): Promise<EngramChunk[]> {
  const res = await fetch(ENGRAM_ENDPOINT, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query, limit }),
    signal,                                    // 审查 IMPORTANT-2：传 AbortSignal
  })
  if (!res.ok) {
    throw new Error(`engram recall failed: ${res.status}`)
  }
  const json = await res.json()
  return json.chunks ?? []
}

export function useEngramRecall(
  query: string,
  options: UseEngramRecallOptions = {}
): UseEngramRecallResult {
  const { limit = 5, staleTime = 60_000, enabled = true } = options

  const result = useQuery<EngramChunk[]>({
    queryKey: ['engram', 'recall', query, limit],
    queryFn: ({ signal }) => recallChunks(query, limit, signal),  // ← signal 自动
    staleTime,
    // query 为空时不请求（enabled=false 让 isLoading=false）
    enabled: enabled && query.trim().length > 0,
  })

  return {
    data: result.data ?? [],
    isLoading: result.isLoading,
    isFetching: result.isFetching,              // 审查 P3
    error: result.error instanceof Error ? result.error : null,
    refetch: result.refetch,
  }
}
