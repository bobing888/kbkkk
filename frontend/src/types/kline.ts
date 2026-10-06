/** K线数据类型（对齐后端 API 响应） */
export interface KLineData {
  datetime: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  [key: string]: unknown
}

/** lightweight-charts 需要的 time 格式 */
export type ChartTime = string | number

export interface CandleData {
  time: ChartTime
  open: number
  high: number
  low: number
  close: number
}

/** 后端返回的 K线 API 响应 */
export interface KLineResponse {
  source: 'cache' | 'fresh'
  count?: number
  data: KLineData[]
}

/** 指标类型 */
export type IndicatorType = 'MA5' | 'MA10' | 'MA20' | 'MA60' | 'MA120' | 'MA200'
