/** TanStack Query hooks for 分析端点 */
import { useQuery } from '@tanstack/react-query'
import {
  fetchIndicators,
  fetchPatterns,
  fetchSignals,
  fetchAnalysis,
} from '../api/analysisApi'
import type { Period, Market } from '../api/klineApi'

export function useIndicators(symbol: string, period: Period, market: Market) {
  return useQuery({
    queryKey: ['indicators', symbol, period, market],
    queryFn: () => fetchIndicators(symbol, period, market),
    staleTime: 5 * 60 * 1000,
    enabled: symbol.length > 0,
  })
}

export function usePatterns(symbol: string, period: Period, market: Market, limit = 30) {
  return useQuery({
    queryKey: ['patterns', symbol, period, market, limit],
    queryFn: () => fetchPatterns(symbol, period, market, limit),
    staleTime: 5 * 60 * 1000,
    enabled: symbol.length > 0,
  })
}

export function useSignals(symbol: string, period: Period, market: Market) {
  return useQuery({
    queryKey: ['signals', symbol, period, market],
    queryFn: () => fetchSignals(symbol, period, market),
    staleTime: 60 * 1000, // 信号 1 分钟刷新
    enabled: symbol.length > 0,
  })
}

export function useAnalysis(symbol: string, period: Period, market: Market, limit = 30) {
  return useQuery({
    queryKey: ['analysis', symbol, period, market, limit],
    queryFn: () => fetchAnalysis(symbol, period, market, limit),
    staleTime: 5 * 60 * 1000,
    enabled: symbol.length > 0,
  })
}
