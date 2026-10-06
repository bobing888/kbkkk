/** 分析 API 客户端 - 调用 4 个 /api/v1/* 端点
 *  - indicators: 6 大指标族
 *  - patterns: K线形态
 *  - signals: 共振买卖信号
 *  - analysis: 聚合（一次 RTT 拿全）
 */
import type {
  IndicatorsResponse,
  PatternsResponse,
  SignalsResponse,
  AnalysisResponse,
} from '../types/analysis'
import type { Period, Market } from './klineApi'

const API_BASE = import.meta.env.VITE_API_BASE
if (!API_BASE) {
  throw new Error('VITE_API_BASE environment variable is required')
}

function buildUrl(symbol: string, endpoint: string, period: Period, market: Market, extra?: Record<string, string>): string {
  const params = new URLSearchParams({ period, market, ...(extra ?? {}) })
  return `${API_BASE}/api/v1/${endpoint}/${encodeURIComponent(symbol)}?${params}`
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return (await res.json()) as T
}

export async function fetchIndicators(
  symbol: string,
  period: Period,
  market: Market
): Promise<IndicatorsResponse> {
  return getJson<IndicatorsResponse>(buildUrl(symbol, 'indicators', period, market))
}

export async function fetchPatterns(
  symbol: string,
  period: Period,
  market: Market,
  limit = 30
): Promise<PatternsResponse> {
  return getJson<PatternsResponse>(buildUrl(symbol, 'patterns', period, market, { limit: String(limit) }))
}

export async function fetchSignals(
  symbol: string,
  period: Period,
  market: Market
): Promise<SignalsResponse> {
  return getJson<SignalsResponse>(buildUrl(symbol, 'signals', period, market))
}

export async function fetchAnalysis(
  symbol: string,
  period: Period,
  market: Market,
  limit = 30
): Promise<AnalysisResponse> {
  return getJson<AnalysisResponse>(buildUrl(symbol, 'analysis', period, market, { limit: String(limit) }))
}
