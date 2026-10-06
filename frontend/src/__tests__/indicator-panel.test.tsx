/**
 * IndicatorPanel 容器测试 — V2 §3.3 + §10 #1 强制
 * TDD 铁律：先写失败测试
 * 骨架屏 100% 覆盖（B7 自检）
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { IndicatorPanel } from '../components/indicators/IndicatorPanel'
import { DEFAULT_ENABLED_INDICATORS } from '../constants/indicators'
import type { IndicatorsData } from '../types/analysis'

// ─── 测试数据 fixtures — BTC/ETH（V2 §1 强制）──────────────────────────
const mockIndicatorData: Record<string, IndicatorsData[string]> = {
  MA: { MA5: 42150.25, MA10: 41980.50, MA20: 41800.00 },
  EMA: { MA5: 42180.00, MA10: 42000.00 },
  MACD: { DIF: 125.34, DEA: 98.50, MACD: 53.68 },
  KDJ: { K: 72.5, D: 68.3, J: 81.0 },
}

const defaultProps = {
  enabledIndicators: DEFAULT_ENABLED_INDICATORS,
  onToggle: vi.fn(),
  data: mockIndicatorData,
  loading: false,
  error: null,
}

// ─── 测试 ───────────────────────────────────────────────────────────────
describe('IndicatorPanel', () => {
  it('test_IndicatorPanel_renders_4_core_by_default', () => {
    render(<IndicatorPanel {...defaultProps} />)
    for (const name of DEFAULT_ENABLED_INDICATORS) {
      expect(screen.getByTestId(`indicator-card-${name}`)).toBeInTheDocument()
    }
  })

  it('test_IndicatorPanel_toggles_indicator', async () => {
    const user = userEvent.setup()
    // 切换 core 视图中的指标
    render(<IndicatorPanel {...defaultProps} enabledIndicators={['MA']} />)
    // MA 在 core 视图中，应存在
    expect(screen.getByTestId('indicator-card-MA')).toBeInTheDocument()
    // 点击切换
    await user.click(screen.getByTestId('indicator-card-MA'))
    expect(defaultProps.onToggle).toHaveBeenCalledWith('MA')
  })

  it('test_IndicatorPanel_collapses_panel', async () => {
    const user = userEvent.setup()
    render(<IndicatorPanel {...defaultProps} />)
    const toggleBtn = screen.getByTestId('panel-collapse-toggle')
    await user.click(toggleBtn)
    // 折叠后网格添加 hidden class
    const grid = screen.getByTestId('indicator-grid')
    expect(grid).toHaveClass('hidden')
  })

  it('test_IndicatorPanel_handles_loading_state', () => {
    // 骨架屏 100% 覆盖（B7 自检）
    render(<IndicatorPanel {...defaultProps} loading={true} data={{}} />)
    // 4 个骨架卡（4 核心）
    for (const name of DEFAULT_ENABLED_INDICATORS) {
      expect(screen.getByTestId(`indicator-skeleton-${name}`)).toBeInTheDocument()
    }
    // 无数据卡
    expect(screen.queryByTestId('indicator-card-MA')).not.toBeInTheDocument()
  })

  it('test_IndicatorPanel_handles_error_state', () => {
    render(<IndicatorPanel {...defaultProps} error="网络错误" />)
    expect(screen.getByText('网络错误')).toBeInTheDocument()
  })

  it('test_IndicatorPanel_handles_empty_data', () => {
    render(<IndicatorPanel {...defaultProps} data={{}} />)
    expect(screen.getByText(/暂无数据/i)).toBeInTheDocument()
  })

  it('test_IndicatorPanel_responsive_grid_desktop_4cols', () => {
    render(<IndicatorPanel {...defaultProps} />)
    const grid = screen.getByTestId('indicator-grid')
    expect(grid).toHaveClass('grid-cols-2', 'md:grid-cols-2', 'lg:grid-cols-4')
  })

  it('test_IndicatorPanel_disabled_indicator_not_rendered', () => {
    // 非 core 视图中，未启用的指标仍然显示（disabled 状态）
    render(<IndicatorPanel {...defaultProps} enabledIndicators={['MA']} />)
    // MA 启用 → 正常显示
    expect(screen.getByTestId('indicator-card-MA')).toBeInTheDocument()
    // EMA 未启用但 core → 显示（disabled 样式）
    const emaCard = screen.getByTestId('indicator-card-EMA')
    expect(emaCard).toBeInTheDocument()
    expect(emaCard).toHaveClass('opacity-50')
  })
})
