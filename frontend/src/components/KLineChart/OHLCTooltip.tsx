/**
 * OHLC Tooltip — K线十字光标跟随 tooltip
 * M3 3.2：V2 §3.2 强制：OHLC tooltip 跟随十字光标
 * License: Original work for kbkkk project.
 */
import { memo, useEffect, useRef } from 'react'
import type { IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts'

interface TooltipData {
  open: number
  high: number
  low: number
  close: number
  volume?: number
  time: string
}

interface OHLCTooltipProps {
  chart: IChartApi | null
  series: ISeriesApi<'Candlestick'> | null
  containerRef: React.RefObject<HTMLDivElement | null>
}

function formatPrice(v: number): string {
  return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatDate(time: string): string {
  return time.replace('T', ' ').slice(0, 16)
}

/**
 * OHLC tooltip div，绝对定位，跟随 lightweight-charts crosshair。
 * 接收 chart + series ref，在 crosshair 移动时更新 tooltip 内容。
 */
export const OHLCTooltip = memo(function OHLCTooltip({
  chart,
  series,
  containerRef,
}: OHLCTooltipProps) {
  const tooltipRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!chart || !series) return

    const handleCrosshairMove = (param: { time?: Time; seriesData: Map<ISeriesApi, CandlestickData<Time> | null> }) => {
      const tooltip = tooltipRef.current
      if (!tooltip) return

      const candle = param.seriesData.get(series) as CandlestickData<Time> | null | undefined
      if (!candle || !param.time) {
        tooltip.style.display = 'none'
        return
      }

      const timeStr = String(param.time)
      const date = formatDate(timeStr)
      const isUp = candle.close >= candle.open
      const color = isUp ? '#16c784' : '#ea3943'

      tooltip.innerHTML = `
        <div class="ohlc-tooltip-row">
          <span class="ohlc-label">O</span><span class="ohlc-value">${formatPrice(candle.open)}</span>
          <span class="ohlc-label">H</span><span class="ohlc-value" style="color:#16c784">${formatPrice(candle.high)}</span>
          <span class="ohlc-label">L</span><span class="ohlc-value" style="color:#ea3943">${formatPrice(candle.low)}</span>
          <span class="ohlc-label">C</span><span class="ohlc-value" style="color:${color}">${formatPrice(candle.close)}</span>
        </div>
        <div class="ohlc-time">${date}</div>
      `
      tooltip.style.display = 'block'
    }

    chart.subscribeCrosshairMove(handleCrosshairMove)
    return () => {
      chart.unsubscribeCrosshairMove(handleCrosshairMove)
    }
  }, [chart, series])

  return (
    <div
      ref={tooltipRef}
      data-testid="ohlc-tooltip"
      style={{
        display: 'none',
        position: 'absolute',
        top: '8px',
        left: '50%',
        transform: 'translateX(-50%)',
        background: 'rgba(22, 24, 28, 0.92)',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: '8px',
        padding: '6px 10px',
        fontSize: '12px',
        color: '#e7e9ea',
        zIndex: 10,
        pointerEvents: 'none',
        backdropFilter: 'blur(12px)',
        whiteSpace: 'nowrap',
      }}
    />
  )
}, (prev, next) => prev.chart === next.chart && prev.series === next.series)
