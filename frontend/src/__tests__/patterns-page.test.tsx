/**
 * PatternsPage tests — M3 3.5
 * TDD 铁律：先写失败测试
 * License: Original work for kbkkk project.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PatternsPage } from '../pages/PatternsPage'
import type { PatternItem } from '../types/analysis'

// 使用有效的 pattern names（必须与 patterns.ts 常量匹配）
const mockPatterns: PatternItem[] = [
  {
    datetime: '2024-01-01T00:00:00',
    name: 'HEAD_AND_SHOULDERS_TOP',
    open: 100,
    high: 105,
    low: 95,
    close: 102,
  },
  {
    datetime: '2024-01-02T00:00:00',
    name: 'DOUBLE_TOP',
    open: 98,
    high: 103,
    low: 93,
    close: 101,
  },
  {
    datetime: '2024-01-03T00:00:00',
    name: 'BULL_FLAG',
    open: 99,
    high: 102,
    low: 96,
    close: 100,
  },
]

describe('PatternsPage — M3 3.5', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('test_PatternsPage_renders_page', () => {
    render(<PatternsPage />)
    expect(screen.getByTestId('patterns-page')).toBeInTheDocument()
  })

  it('test_PatternsPage_renders_two_view_tabs', () => {
    render(<PatternsPage />)
    expect(screen.getByTestId('patterns-view-switcher-option-chart')).toBeInTheDocument()
    expect(screen.getByTestId('patterns-view-switcher-option-list')).toBeInTheDocument()
  })

  it('test_PatternsPage_switches_view', async () => {
    render(<PatternsPage patterns={mockPatterns} />)
    await userEvent.click(screen.getByTestId('patterns-view-switcher-option-list'))
    await waitFor(() => {
      expect(screen.getByTestId('pattern-list')).toBeInTheDocument()
    })
  })

  it('test_PatternsPage_renders_chart_view_by_default', () => {
    render(<PatternsPage />)
    expect(screen.getByTestId('patterns-chart-container')).toBeInTheDocument()
  })

  it('test_PatternsPage_handles_loading', () => {
    render(<PatternsPage loading={true} />)
    expect(screen.getByTestId('chart-skeleton')).toBeInTheDocument()
  })

  it('test_PatternsPage_handles_error', () => {
    render(<PatternsPage error="加载失败" />)
    expect(screen.getByTestId('error-message')).toBeInTheDocument()
    expect(screen.getByText(/加载失败/)).toBeInTheDocument()
  })

  it('test_PatternsPage_opens_detail_on_card_click', async () => {
    render(<PatternsPage patterns={mockPatterns} />)
    await userEvent.click(screen.getByTestId('patterns-view-switcher-option-list'))
    await waitFor(() => {
      expect(screen.getByTestId('pattern-list')).toBeInTheDocument()
    })
    // Cards use data-testid="pattern-card-N"
    const cards = screen.getAllByTestId(/^pattern-card-/)
    expect(cards.length).toBeGreaterThan(0)
    await userEvent.click(cards[0])
    expect(screen.getByTestId('pattern-detail-modal')).toBeInTheDocument()
  })

  it('test_PatternsPage_has_filter_buttons', () => {
    render(<PatternsPage patterns={mockPatterns} />)
    expect(screen.getByTestId('filter-all')).toBeInTheDocument()
    expect(screen.getByTestId('filter-reversal')).toBeInTheDocument()
    expect(screen.getByTestId('filter-continuation')).toBeInTheDocument()
    expect(screen.getByTestId('filter-midline')).toBeInTheDocument()
    expect(screen.getByTestId('filter-warning')).toBeInTheDocument()
  })

  it('test_PatternsPage_shows_empty_list_state', async () => {
    render(<PatternsPage patterns={[]} />)
    await userEvent.click(screen.getByTestId('patterns-view-switcher-option-list'))
    await waitFor(() => {
      expect(screen.getByTestId('pattern-list')).toBeInTheDocument()
      expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    })
  })
})
