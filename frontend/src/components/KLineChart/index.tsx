import { useEffect, useRef, type FC } from 'react'
import {
  createChart,
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
} from 'lightweight-charts'
import { ChartSkeleton } from '../common/ChartSkeleton'
import { ErrorMessage } from '../common/ErrorMessage'
import { EmptyState } from '../common/EmptyState'
import type { KLineData, IndicatorType } from '../../types/kline'

interface KLineChartProps {
  symbol: string
  data: KLineData[]
  loading?: boolean
  error?: string
  indicators?: IndicatorType[]
}

/**
 * K线图主组件
 * - 用 useRef + useEffect 调用 lightweight-charts
 * - cleanup 调用 chart.remove() 避免内存泄漏
 * - 4 态：loading / error / empty / success
 */
export const KLineChart: FC<KLineChartProps> = ({
  symbol,
  data,
  loading = false,
  error,
  indicators = [],
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

  // 挂载时创建 chart（v5 API: addSeries + SeriesDefinition）
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: 'currentColor',
      },
      grid: {
        vertLines: { color: 'rgba(128,128,128,0.15)' },
        horzLines: { color: 'rgba(128,128,128,0.15)' },
      },
      width: containerRef.current.clientWidth,
      height: 400,
    })

    chartRef.current = chart
    // v5 API: addSeries(SeriesDefinition, options?)
    seriesRef.current = chart.addSeries(CandlestickSeries)

    // resize 监听
    const resizeObserver = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
        })
      }
    })
    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [])

  // data 变化时更新数据
  useEffect(() => {
    if (!seriesRef.current || data.length === 0) return

    const candleData: CandlestickData<Time>[] = data
      .map((k) => {
        if (!k || typeof k.datetime !== 'string') return null
        return {
          time: k.datetime.slice(0, 10) as Time,
          open: k.open,
          high: k.high,
          low: k.low,
          close: k.close,
        } satisfies CandlestickData<Time>
      })
      .filter((c): c is CandlestickData<Time> => c !== null)

    seriesRef.current.setData(candleData)
    chartRef.current?.timeScale().fitContent()
  }, [data])

  // 指标切换（后续扩展）
  useEffect(() => {
    if (!chartRef.current || data.length === 0) return
    void indicators
    // TODO: 叠加 MA/MAcD 等指标线（markers 标注在 M3.3/M3.4 实现）
  }, [indicators, data])

  // 4 态渲染
  if (loading) {
    return (
      <div
        role="img"
        aria-label={`${symbol} K线图`}
        className="w-full h-full"
      >
        <ChartSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div
        role="img"
        aria-label={`${symbol} K线图`}
        className="w-full h-full"
      >
        <ErrorMessage message={error} />
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div
        role="img"
        aria-label={`${symbol} K线图`}
        className="w-full h-full"
      >
        <EmptyState />
      </div>
    )
  }

  return (
    <div
      role="img"
      aria-label={`${symbol} K线图`}
      className="w-full h-full"
    >
      <div
        data-testid="kline-chart-container"
        ref={containerRef}
        className="w-full h-full"
      />
    </div>
  )
}
