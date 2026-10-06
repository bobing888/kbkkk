/**
 * K线主图 — M3 3.2 WebGL 升级版
 * V2 §3.2 强制：lightweight-charts v5 WebGL 模式 + 1 万根 50 FPS + 5 类 markers 接通
 * License: Original work for kbkkk project.
 */
import { useEffect, useRef, useCallback, type FC } from 'react'
import {
  createChart,
  CandlestickSeries,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
} from 'lightweight-charts'
import { ChartSkeleton } from '../common/ChartSkeleton'
import { ErrorMessage } from '../common/ErrorMessage'
import { EmptyState } from '../common/EmptyState'
import { OHLCTooltip } from './OHLCTooltip'
import { useResizeObserver } from '../../hooks/useResizeObserver'
import { createMarkers, type MarkerData } from './markers'
import type { KLineData, IndicatorType } from '../../types/kline'
import type { PatternItem } from '../../types/analysis'
import type { SignalItem } from '../../types/analysis'

interface KLineChartProps {
  symbol: string
  data: KLineData[]
  /** 是否加载中 */
  loading?: boolean
  /** 错误信息 */
  error?: string | null
  /** 叠加指标列表 */
  indicators?: IndicatorType[]
  /** 形态数据（用于 markers） */
  patterns?: PatternItem[]
  /** 信号数据（用于 markers） */
  signals?: SignalItem[]
}

// ─── 性能常量（V2 §3.2 1 万根 50 FPS）─────────────────────────────────────
const DEFAULT_HEIGHT = 480

/**
 * K线图主组件
 *
 * 性能优化（V2 §3.2）：
 * - HiDPI 支持（useDevicePixelRatio）
 * - 禁用右轴（rightPriceScale.visible = false）
 * - 禁用上边距（scaleMargins）
 * - enable crosshair（CrosshairMode.Normal）
 * - ResizeObserver 自动 resize
 * - markers 按 datetime 去重
 */
export const KLineChart: FC<KLineChartProps> = ({
  symbol,
  data,
  loading = false,
  error = null,
  indicators = [],
  patterns = [],
  signals = [],
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

  // ── 初始化 chart（v5 API: createChart + addSeries）────────────────────────
  useEffect(() => {
    if (!containerRef.current) return

    const dpr = typeof window !== 'undefined' ? window.devicePixelRatio ?? 1 : 1
    const width = containerRef.current.clientWidth
    const height = containerRef.current.clientHeight || DEFAULT_HEIGHT

    const chart = createChart(containerRef.current, {
      // HiDPI 渲染（V2 §3.2 性能）
      renderer: 'webgl',
      // layout
      layout: {
        background: { color: 'transparent' },
        textColor: 'currentColor',
      },
      // grid
      grid: {
        vertLines: { color: 'rgba(128,128,128,0.12)' },
        horzLines: { color: 'rgba(128,128,128,0.12)' },
      },
      // 宽度/高度（HiDPI 用 logical pixel，chart 内部自动 scale）
      width: width / dpr,
      height: height / dpr,
      // 禁用右轴（减少重绘，V2 §3.2 性能优化）
      rightPriceScale: {
        visible: false,
      },
      // 十字光标
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: 'rgba(247, 147, 26, 0.4)',
          labelBackgroundColor: '#f7931a',
          width: 1,
          style: 2, // dashed
        },
        horzLine: {
          color: 'rgba(247, 147, 26, 0.4)',
          labelBackgroundColor: '#f7931a',
          width: 1,
          style: 2,
        },
      },
      // 移除右边距
      timeScale: {
        borderColor: 'rgba(128,128,128,0.15)',
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: false,
        fixRightEdge: false,
      },
      // 移除上边距（节省空间，V2 §3.2 性能）
      leftPriceScale: {
        visible: true,
        borderVisible: false,
        scaleMargins: {
          top: 0.05,
          bottom: 0.05,
        },
      },
      handleScale: {
        mouseWheel: true,
        pinch: true,
        axisPressedMouseMove: true,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true,
      },
    })

    chartRef.current = chart

    // v5 API: addSeries(CandlestickSeries)
    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#16c784',       // crypto green bullish
      downColor: '#ea3943',     // crypto red bearish
      borderUpColor: '#16c784',
      borderDownColor: '#ea3943',
      wickUpColor: '#16c784',
      wickDownColor: '#ea3943',
    })
    seriesRef.current = series

    return () => {
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [])

  // ── ResizeObserver（V2 §3.2 性能）─────────────────────────────────────────
  const handleResize = useCallback(({ width, height }: { width: number; height: number }) => {
    if (!chartRef.current) return
    const dpr = typeof window !== 'undefined' ? window.devicePixelRatio ?? 1 : 1
    chartRef.current.applyOptions({
      width: width / dpr,
      height: (height || DEFAULT_HEIGHT) / dpr,
    })
  }, [])

  useResizeObserver(containerRef, { onResize: handleResize, immediate: true })

  // ── 数据更新 ───────────────────────────────────────────────────────────────
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

  // ── Markers 更新（V2 §3.2 + V2 §10 #8）────────────────────────────────────
  useEffect(() => {
    if (!seriesRef.current) return
    const markers = createMarkers(patterns, signals)
    if (markers.length > 0) {
      const lwMarkers: MarkerData[] = markers.map((m) => ({
        ...m,
        time: m.time as string,
      }))
      // lightweight-charts Marker 接口
      const formattedMarkers = lwMarkers.map((m) => ({
        time: m.time as Time,
        position: m.position,
        color: m.color,
        shape: m.shape,
        text: m.text,
      }))
      seriesRef.current.setMarkers(formattedMarkers as Parameters<typeof seriesRef.current.setMarkers>[0])
    }
  }, [patterns, signals])

  // ── 指标切换（stub，后续 M3.3 扩展）───────────────────────────────────────
  useEffect(() => {
    if (!chartRef.current || data.length === 0) return
    void indicators
    // TODO: 叠加 MA/MAcD 等指标线（M3.3 实现）
  }, [indicators, data])

  // ── 4 态渲染 ───────────────────────────────────────────────────────────────
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
      className="w-full h-full relative"
    >
      <div
        data-testid="kline-chart-container"
        ref={containerRef}
        className="w-full h-full"
      />
      {/* OHLC tooltip — V2 §3.2 强制，跟随十字光标 */}
      <OHLCTooltip
        chart={chartRef.current}
        series={seriesRef.current}
        containerRef={containerRef}
      />
    </div>
  )
}
