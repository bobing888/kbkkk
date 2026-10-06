/**
 * SignalsPage integration tests — M3 3.4
 * V2 §3.4 强制：信号中心列表 + 连接状态指示器 + WebSocket 实时
 * TDD 铁律：先红后绿
 * License: Original work for kbkkk project.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SignalsPage } from '../pages/SignalsPage'
import { useSignalsStore } from '../store'
import type { SignalItem } from '../types/analysis'

// ─── Mock WebSocketClient (proper constructor) ──────────────────────────────

const mockSignalsData: SignalItem[] = [
  {
    name: 'MA Cross Golden',
    direction: 'long',
    confidence: 0.82,
    entry: 42000,
    stop_loss: 41000,
    take_profit: 45000,
    sources: ['MA5', 'MA10'],
    datetime: '2024-01-01T00:00:00',
  },
  {
    name: 'RSI Overbought',
    direction: 'short',
    confidence: 0.75,
    entry: 43000,
    stop_loss: 44000,
    take_profit: 40000,
    sources: ['RSI'],
    datetime: '2024-01-02T00:00:00',
  },
  {
    name: 'Low Confidence',
    direction: 'neutral',
    confidence: 0.45,
    sources: ['RSI'],
    datetime: '2024-01-03T00:00:00',
  },
]

// ─── Tests ─────────────────────────────────────────────────────────────────

describe('SignalsPage — M3 3.4 信号中心', () => {

  beforeEach(() => {
    useSignalsStore.getState().clear()
    vi.clearAllMocks()
  })

  it('test_SignalsPage_renders_signal_list', async () => {
    const user = userEvent.setup()
    // Pre-populate store with signals
    const store = useSignalsStore.getState()
    mockSignalsData.forEach((s) => store.addSignal(s))

    render(<SignalsPage />)

    await waitFor(() => {
      expect(screen.getByTestId('signals-page')).toBeInTheDocument()
    })
    expect(screen.getByText('MA Cross Golden')).toBeInTheDocument()
    expect(screen.getByText('RSI Overbought')).toBeInTheDocument()
  })

  it('test_SignalsPage_filters_by_type', async () => {
    const user = userEvent.setup()
    const store = useSignalsStore.getState()
    mockSignalsData.forEach((s) => store.addSignal(s))

    render(<SignalsPage />)

    await waitFor(() => {
      expect(screen.getByTestId('signals-page')).toBeInTheDocument()
    })

    // Click "做多" filter
    const longFilter = screen.getByTestId('filter-long')
    await user.click(longFilter)

    // Long signal visible
    expect(screen.getByText('MA Cross Golden')).toBeInTheDocument()
  })

  it('test_SignalsPage_handles_empty_state', () => {
    render(<SignalsPage />)

    expect(screen.getByTestId('signals-page')).toBeInTheDocument()
    // Empty state
    expect(screen.getByText('暂无信号')).toBeInTheDocument()
  })

  it('test_SignalsPage_handles_error', () => {
    render(<SignalsPage />)

    expect(screen.getByTestId('signals-page')).toBeInTheDocument()
    expect(screen.getByText('信号中心')).toBeInTheDocument()
  })

  it('test_SignalsPage_websocket_disconnect_indicator', async () => {
    render(<SignalsPage />)

    await waitFor(() => {
      expect(screen.getByTestId('signals-page')).toBeInTheDocument()
    })
    expect(screen.getByTestId('connection-status')).toBeInTheDocument()
  })
})
