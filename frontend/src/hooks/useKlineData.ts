import { useQuery } from '@tanstack/react-query'
import { fetchKLine, type Period, type Market } from '../api/klineApi'
import type { KLineData } from '../types/kline'

export interface UseKLineDataOptions {
  symbol: string
  period: Period
  market: Market
  /** 起始日期 YYYYMMDD */
  start?: string
  /** 结束日期 YYYYMMDD */
  end?: string
}

export interface UseKLineDataResult {
  data: KLineData[]
  source?: 'cache' | 'fresh'
}

/** TanStack Query hook for K线数据 */
export function useKLineData({ symbol, period, market, start, end }: UseKLineDataOptions) {
  return useQuery<UseKLineDataResult, Error>({
    queryKey: ['kline', symbol, period, market, start, end],
    queryFn: () => fetchKLine(symbol, period, market, { start, end }),
    // staleTime 5min = 缓存层 TTL 对齐
    staleTime: 5 * 60 * 1000,
    // 后端故障时不要无限重试
    retry: 2,
    enabled: symbol.length > 0,
  })
}
