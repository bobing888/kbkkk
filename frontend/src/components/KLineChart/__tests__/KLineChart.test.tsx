import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { KLineChart } from '../index'
import type { KLineData } from '../../../types/kline'

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
vi.mock('../../hooks/useResizeObserver', () => ({
  useResizeObserver: vi.fn(),
}))

// Mock useDevicePixelRatio
vi.mock('../useDevicePixelRatio', () => ({
  useDevicePixelRatio: vi.fn(() => 1),
}))

// Mock React Router hooks
vi.mock('react-router-dom', () => ({
  useSearchParams: vi.fn(() => {
    const params = new URLSearchParams()
    return [params, vi.fn()]
  }),
}))

const mockData: KLineData[] = [
  { datetime: '2024-01-01T00:00:00', open: 100, high: 105, low: 98, close: 103, volume: 1000 },
  { datetime: '2024-01-02T00:00:00', open: 103, high: 110, low: 102, close: 108, volume: 1200 },
  { datetime: '2024-01-03T00:00:00', open: 108, high: 112, low: 107, close: 111, volume: 800 },
]

describe('KLineChart', () => {
  it('renders a container with accessible name', () => {
    render(<KLineChart symbol="BTC/USDT" data={[]} />)
    expect(screen.getByRole('img', { name: /K线图/i })).toBeInTheDocument()
  })

  it('shows skeleton when loading prop is true and data is empty', () => {
    render(<KLineChart symbol="BTC/USDT" data={[]} loading={true} />)
    expect(screen.getByTestId('chart-skeleton')).toBeInTheDocument()
  })

  it('renders error message when error prop is provided', () => {
    render(<KLineChart symbol="BTC/USDT" data={[]} error="API 500" />)
    expect(screen.getByText(/API 500/)).toBeInTheDocument()
  })

  it('renders empty state when data array is empty and not loading', () => {
    render(<KLineChart symbol="BTC/USDT" data={[]} />)
    expect(screen.getByText(/暂无数据/i)).toBeInTheDocument()
  })

  it('renders chart container when data is provided', () => {
    render(<KLineChart symbol="BTC/USDT" data={mockData} />)
    // Chart container should be present
    expect(screen.getByTestId('kline-chart-container')).toBeInTheDocument()
  })

  it('accepts indicators prop without crashing', () => {
    render(
      <KLineChart
        symbol="BTC/USDT"
        data={mockData}
        indicators={['MA5', 'MA10', 'MA20']}
      />
    )
    expect(screen.getByTestId('kline-chart-container')).toBeInTheDocument()
  })
})
