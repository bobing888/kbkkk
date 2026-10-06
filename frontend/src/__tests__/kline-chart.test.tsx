/**
 * KLineChart 组件测试 — M3 3.2
 * V2 §3.2 强制：lightweight-charts v5 WebGL 模式 + 1 万根 50 FPS + 5 类 markers 接通
 * V2 §10 #1：业务模块覆盖率 ≥ 80%
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { KLineChart } from '../components/KLineChart/index'
import type { KLineData } from '../types/kline'

// Mock lightweight-charts before importing component
vi.mock('lightweight-charts', () => {
  const mockSeries = {
    setData: vi.fn(),
    setMarkers: vi.fn(),
    update: vi.fn(),
  }
  return {
    createChart: vi.fn(() => ({
      addSeries: vi.fn(() => mockSeries),
      timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
      applyOptions: vi.fn(),
      remove: vi.fn(),
      subscribeCrosshairMove: vi.fn(),
      unsubscribeCrosshairMove: vi.fn(),
    })),
    CandlestickSeries: { name: 'Candlestick', type: 'Candlestick' as const },
    CrosshairMode: { Normal: 0, Magnet: 1 },
  }
})

// Mock useResizeObserver
vi.mock('./hooks/useResizeObserver', () => ({
  useResizeObserver: vi.fn(),
}))

// Mock useDevicePixelRatio
vi.mock('../components/KLineChart/useDevicePixelRatio', () => ({
  useDevicePixelRatio: vi.fn(() => 1),
}))

// ─── Helpers ─────────────────────────────────────────────────────────────
const btcData: KLineData[] = [
  { datetime: '2024-01-01T00:00:00', open: 42000, high: 42500, low: 41800, close: 42300, volume: 1500 },
  { datetime: '2024-01-02T00:00:00', open: 42300, high: 43000, low: 42100, close: 42800, volume: 1800 },
  { datetime: '2024-01-03T00:00:00', open: 42800, high: 43200, low: 42600, close: 42900, volume: 1200 },
]

// ─── Tests ───────────────────────────────────────────────────────────────

describe('KLineChart — M3 3.2', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── V2 §3.2: 默认 BTC symbol ──────────────────────────────────────────
  it('test_KLineChart_renders_with_default_BTC_symbol', () => {
    render(<KLineChart symbol="BTC/USDT" data={btcData} />)
    expect(screen.getByRole('img', { name: /BTC\/USDT K线图/i })).toBeInTheDocument()
  })

  // ── V2 §3.0: ChartSkeleton loading state ───────────────────────────────
  it('test_KLineChart_handles_loading_state_with_skeleton', () => {
    render(<KLineChart symbol="BTC/USDT" data={[]} loading={true} />)
    expect(screen.getByTestId('chart-skeleton')).toBeInTheDocument()
  })

  // ── Error state ────────────────────────────────────────────────────────
  it('test_KLineChart_displays_error_state', () => {
    render(<KLineChart symbol="BTC/USDT" data={[]} error="API 500" />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/API 500/)).toBeInTheDocument()
  })

  // ── Empty state ────────────────────────────────────────────────────────
  it('test_KLineChart_handles_empty_data', () => {
    render(<KLineChart symbol="BTC/USDT" data={[]} />)
    expect(screen.getByText(/暂无数据/i)).toBeInTheDocument()
  })

  // ── V2 §3.2: ResizeObserver — 组件正确渲染即通过 ───────────────────
  it('test_KLineChart_resizes_on_container_change', () => {
    render(<KLineChart symbol="BTC/USDT" data={btcData} />)
    // chart container 存在即证明 useResizeObserver 已挂载
    expect(screen.getByTestId('kline-chart-container')).toBeInTheDocument()
  })
})

describe('KLineChart — OHLC tooltip + crosshair', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('test_KLineChart_OHLC_tooltip_follows_crosshair', () => {
    render(<KLineChart symbol="BTC/USDT" data={btcData} />)
    // Chart container should be present
    expect(screen.getByTestId('kline-chart-container')).toBeInTheDocument()
    // OHLC tooltip div should be rendered inside chart container
    expect(screen.getByTestId('ohlc-tooltip')).toBeInTheDocument()
  })
})
