import type { KLineResponse } from '../types/kline'

const API_BASE = import.meta.env.VITE_API_BASE
if (!API_BASE) {
  throw new Error('VITE_API_BASE environment variable is required')
}

function validateSymbol(symbol: string): string {
  if (!/^[A-Za-z0-9/_-]{1,32}$/.test(symbol)) {
    throw new TypeError(`Invalid symbol format: ${symbol}`)
  }
  return symbol
}

export type Period = '1m' | '5m' | '15m' | '30m' | '60m' | '1d' | '1w' | '1M'
export type Market = 'cn' | 'us' | 'crypto'

export async function fetchKLine(
  symbol: string,
  period: Period,
  market: Market,
  options?: { start?: string; end?: string }
): Promise<KLineResponse> {
  const safeSymbol = validateSymbol(symbol)
  const params = new URLSearchParams({ period, market })
  if (options?.start) params.set('start', options.start)
  if (options?.end) params.set('end', options.end)

  const url = `${API_BASE}/api/v1/kline/${encodeURIComponent(safeSymbol)}?${params}`
  const res = await fetch(url)

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }

  return res.json() as Promise<KLineResponse>
}
