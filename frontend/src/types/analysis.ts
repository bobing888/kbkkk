/** 11 个技术指标（6 大族），对齐后端 /api/v1/indicators 响应 */

export interface MaValues {
  MA5?: number
  MA10?: number
  MA20?: number
  MA60?: number
  MA120?: number
  MA250?: number
}

export interface MacdValues {
  DIF?: number
  DEA?: number
  MACD?: number
}

export interface BollValues {
  BOLL_MID?: number
  BOLL_UPPER?: number
  BOLL_LOWER?: number
}

export interface KdjValues {
  K?: number
  D?: number
  J?: number
}

export interface IndicatorsData {
  MA?: MaValues
  MACD?: MacdValues
  RSI?: number
  BOLL?: BollValues
  KDJ?: KdjValues
  OBV?: number
}

export interface IndicatorsResponse {
  symbol: string
  period: string
  market: string
  datetime?: string
  indicators: IndicatorsData
}

/** K 线形态（对齐 /api/v1/patterns 响应）*/

export interface PatternItem {
  datetime: string
  name: string
  open: number
  high: number
  low: number
  close: number
}

export interface PatternsResponse {
  symbol: string
  period: string
  market: string
  count: number
  patterns: PatternItem[]
}

/** 交易信号（对齐 /api/v1/signals 响应） */

export type SignalDirection = 'long' | 'short' | 'neutral'

export interface SignalItem {
  name: string
  direction: SignalDirection
  confidence: number
  entry?: number
  stop_loss?: number
  take_profit?: number
  sources: string[]
  datetime?: string
}

export interface SignalsResponse {
  symbol: string
  period: string
  market: string
  count: number
  signals: SignalItem[]
}

/** 聚合响应 */

export interface AnalysisResponse {
  symbol: string
  period: string
  market: string
  datetime?: string
  indicators: IndicatorsData
  patterns: PatternItem[]
  signals: SignalItem[]
}
