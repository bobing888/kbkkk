/**
 * IndicatorCard 组件测试 — V2 §3.3 + §10 #1 强制
 * TDD 铁律：先写失败测试
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { IndicatorCard } from '../components/indicators/IndicatorCard'
import { INDICATOR_MAP } from '../constants/indicators'

// ─── 辅助 ───────────────────────────────────────────────────────────────
const defaultProps = {
  name: 'RSI',
  value: 65.42,
  loading: false,
  error: null,
  enabled: true,
}

const renderCard = (overrides = {}) =>
  render(<IndicatorCard {...defaultProps} {...overrides} />)

// ─── 测试 ───────────────────────────────────────────────────────────────
describe('IndicatorCard', () => {
  it('test_IndicatorCard_renders_name_and_value', () => {
    renderCard({ name: 'MA', value: 45123.45 })
    // 显示 displayName，不只是 name
    expect(screen.getByText('均线 (MA)')).toBeInTheDocument()
    expect(screen.getByText('45,123.45')).toBeInTheDocument()
  })

  it('test_IndicatorCard_formats_decimal_precision', () => {
    // RSI → 2 位小数 + %
    renderCard({ name: 'RSI', value: 65.123456 })
    expect(screen.getByText('65.12%')).toBeInTheDocument()
  })

  it('test_IndicatorCard_formats_rsi_with_percent', () => {
    renderCard({ name: 'RSI', value: 72.5 })
    expect(screen.getByText('72.50%')).toBeInTheDocument()
  })

  it('test_IndicatorCard_formats_macd_4_decimals', () => {
    renderCard({ name: 'MACD', value: 0.01234 })
    expect(screen.getByText('0.0123')).toBeInTheDocument()
  })

  it('test_IndicatorCard_shows_change_indicator_up', () => {
    renderCard({ name: 'MA', value: 100, previousValue: 95 })
    const upArrow = screen.getByTestId('change-indicator-up')
    expect(upArrow).toBeInTheDocument()
    expect(screen.queryByTestId('change-indicator-down')).not.toBeInTheDocument()
  })

  it('test_IndicatorCard_shows_change_indicator_down', () => {
    renderCard({ name: 'MA', value: 95, previousValue: 100 })
    expect(screen.getByTestId('change-indicator-down')).toBeInTheDocument()
    expect(screen.queryByTestId('change-indicator-up')).not.toBeInTheDocument()
  })

  it('test_IndicatorCard_handles_loading_state', () => {
    renderCard({ loading: true })
    expect(screen.getByTestId('indicator-card-skeleton')).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })

  it('test_IndicatorCard_handles_error_state', () => {
    renderCard({ error: '数据加载失败' })
    expect(screen.getByText('数据加载失败')).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })

  it('test_IndicatorCard_disabled_state', () => {
    renderCard({ enabled: false })
    const card = screen.getByTestId('indicator-card-RSI')
    expect(card).toHaveClass('opacity-50')
  })

  it('test_IndicatorCard_calls_onToggle', async () => {
    const user = userEvent.setup()
    const onToggle = vi.fn()
    renderCard({ onToggle })
    await user.click(screen.getByTestId('indicator-card-RSI'))
    expect(onToggle).toHaveBeenCalledOnce()
  })

  it('test_IndicatorCard_shows_no_value_placeholder', () => {
    renderCard({ value: null })
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})
