/**
 * SignalCard component tests — M3 3.4
 * V2 §3.4 强制：5 类信号玻璃卡
 * TDD 铁律：先红后绿
 * License: Original work for kbkkk project.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { SignalItem } from '../types/analysis'
import { SignalCard } from '../components/signals/SignalCard'

// ─── Mock data ─────────────────────────────────────────────────────────────

const baseSignal: SignalItem = {
  name: 'MA Cross Golden',
  direction: 'long',
  confidence: 0.82,
  entry: 42000,
  stop_loss: 41000,
  take_profit: 45000,
  sources: ['MA5', 'MA10'],
  datetime: '2024-01-01T00:00:00',
}

// ─── Tests ─────────────────────────────────────────────────────────────────

describe('SignalCard — M3 3.4 5 类信号卡', () => {

  it('test_SignalCard_renders_buy_signal', () => {
    render(<SignalCard signal={baseSignal} />)

    expect(screen.getByText('MA Cross Golden')).toBeInTheDocument()
    expect(screen.getByText('做多')).toBeInTheDocument()
    expect(screen.getByText(/82%/)).toBeInTheDocument()
    expect(screen.getByText('42,000.00')).toBeInTheDocument()
  })

  it('test_SignalCard_renders_sell_signal', () => {
    const sellSignal: SignalItem = {
      ...baseSignal,
      name: 'RSI Overbought',
      direction: 'short',
      confidence: 0.75,
      entry: 43000,
      stop_loss: 44000,
      take_profit: 40000,
      datetime: '2024-01-02T00:00:00',
    }
    render(<SignalCard signal={sellSignal} />)

    expect(screen.getByText('RSI Overbought')).toBeInTheDocument()
    expect(screen.getByText('做空')).toBeInTheDocument()
    expect(screen.getByText(/75%/)).toBeInTheDocument()
  })

  it('test_SignalCard_renders_warning_signal', () => {
    const warningSignal: SignalItem = {
      ...baseSignal,
      name: 'Low Confidence',
      direction: 'neutral',
      confidence: 0.45,
      entry: 42000,
      stop_loss: undefined,
      take_profit: undefined,
    }
    render(<SignalCard signal={warningSignal} />)

    expect(screen.getByText('中性')).toBeInTheDocument()
    expect(screen.getByText(/45%/)).toBeInTheDocument()
  })

  it('test_SignalCard_shows_confidence', () => {
    const signal: SignalItem = {
      ...baseSignal,
      confidence: 0.91,
    }
    render(<SignalCard signal={signal} />)

    expect(screen.getByText(/91%/)).toBeInTheDocument()
  })

  it('test_SignalCard_shows_timestamp', () => {
    render(<SignalCard signal={baseSignal} />)

    expect(screen.getByText('2024-01-01')).toBeInTheDocument()
  })

  it('test_SignalCard_handles_click', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(<SignalCard signal={baseSignal} onClick={onClick} />)

    await user.click(screen.getByTestId('signal-card'))

    expect(onClick).toHaveBeenCalledOnce()
  })
})
