/**
 * PatternDetailModal tests — M3 3.5
 * TDD 铁律：先写失败测试
 * License: Original work for kbkkk project.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PatternDetailModal } from '../components/patterns/PatternDetailModal'
import type { PatternItem } from '../types/analysis'
import type { PatternDef } from '../constants/patterns'

const mockPatternDef: PatternDef = {
  name: 'HEAD_AND_SHOULDERS_TOP',
  displayName: '头肩顶',
  category: 'reversal',
  description: '看跌反转形态，由三个峰值组成，中间峰值最高。',
  icon: '👕',
}

const mockPatternItem: PatternItem = {
  datetime: '2024-01-01T00:00:00',
  name: 'HEAD_AND_SHOULDERS_TOP',
  open: 100,
  high: 105,
  low: 95,
  close: 102,
}

describe('PatternDetailModal — M3 3.5', () => {
  it('test_PatternDetailModal_renders_when_open', () => {
    render(
      <PatternDetailModal
        pattern={mockPatternItem}
        def={mockPatternDef}
        isOpen={true}
        onClose={vi.fn()}
      />
    )
    expect(screen.getByTestId('pattern-detail-modal')).toBeInTheDocument()
  })

  it('test_PatternDetailModal_not_render_when_closed', () => {
    render(
      <PatternDetailModal
        pattern={mockPatternItem}
        def={mockPatternDef}
        isOpen={false}
        onClose={vi.fn()}
      />
    )
    expect(screen.queryByTestId('pattern-detail-modal')).not.toBeInTheDocument()
  })

  it('test_PatternDetailModal_shows_name', () => {
    render(
      <PatternDetailModal
        pattern={mockPatternItem}
        def={mockPatternDef}
        isOpen={true}
        onClose={vi.fn()}
      />
    )
    expect(screen.getByText('头肩顶')).toBeInTheDocument()
  })

  it('test_PatternDetailModal_shows_description', () => {
    render(
      <PatternDetailModal
        pattern={mockPatternItem}
        def={mockPatternDef}
        isOpen={true}
        onClose={vi.fn()}
      />
    )
    expect(screen.getByText(/看跌反转形态/)).toBeInTheDocument()
  })

  it('test_PatternDetailModal_shows_datetime', () => {
    render(
      <PatternDetailModal
        pattern={mockPatternItem}
        def={mockPatternDef}
        isOpen={true}
        onClose={vi.fn()}
      />
    )
    expect(screen.getByText('2024-01-01')).toBeInTheDocument()
  })

  it('test_PatternDetailModal_shows_price_range', () => {
    render(
      <PatternDetailModal
        pattern={mockPatternItem}
        def={mockPatternDef}
        isOpen={true}
        onClose={vi.fn()}
      />
    )
    // formatPrice adds 2 decimal places: 105 → 105.00, 95 → 95.00
    expect(screen.getByText('105.00')).toBeInTheDocument()
    expect(screen.getByText('95.00')).toBeInTheDocument()
  })

  it('test_PatternDetailModal_closes_on_overlay_click', async () => {
    const onClose = vi.fn()
    render(
      <PatternDetailModal
        pattern={mockPatternItem}
        def={mockPatternDef}
        isOpen={true}
        onClose={onClose}
      />
    )
    await userEvent.click(screen.getByTestId('pattern-modal-overlay'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('test_PatternDetailModal_closes_on_escape', async () => {
    const onClose = vi.fn()
    render(
      <PatternDetailModal
        pattern={mockPatternItem}
        def={mockPatternDef}
        isOpen={true}
        onClose={onClose}
      />
    )
    await userEvent.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('test_PatternDetailModal_shows_category_badge', () => {
    render(
      <PatternDetailModal
        pattern={mockPatternItem}
        def={mockPatternDef}
        isOpen={true}
        onClose={vi.fn()}
      />
    )
    expect(screen.getByText('反转')).toBeInTheDocument()
  })

  it('test_PatternDetailModal_shows_close_button', () => {
    render(
      <PatternDetailModal
        pattern={mockPatternItem}
        def={mockPatternDef}
        isOpen={true}
        onClose={vi.fn()}
      />
    )
    expect(screen.getByTestId('pattern-modal-close')).toBeInTheDocument()
  })
})
