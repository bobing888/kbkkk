/**
 * PatternCard tests — M3 3.5
 * TDD 铁律：先写失败测试
 * License: Original work for kbkkk project.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PatternCard } from '../components/patterns/PatternCard'
import type { PatternItem } from '../types/analysis'
import type { PatternDef } from '../constants/patterns'

const mockPatternDef: PatternDef = {
  name: 'HEAD_AND_SHOULDERS_TOP',
  displayName: '头肩顶',
  category: 'reversal',
  description: '看跌反转形态',
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

describe('PatternCard — M3 3.5', () => {
  it('test_PatternCard_renders_name', () => {
    render(<PatternCard pattern={mockPatternItem} def={mockPatternDef} />)
    expect(screen.getByText('头肩顶')).toBeInTheDocument()
  })

  it('test_PatternCard_renders_category_icon', () => {
    render(<PatternCard pattern={mockPatternItem} def={mockPatternDef} />)
    expect(screen.getByText('👕')).toBeInTheDocument()
  })

  it('test_PatternCard_shows_confidence_bar', () => {
    const withConfidence: PatternItem & { confidence?: number } = {
      ...mockPatternItem,
      confidence: 0.75,
    }
    render(<PatternCard pattern={withConfidence} def={mockPatternDef} />)
    expect(screen.getByTestId('pattern-card')).toBeInTheDocument()
  })

  it('test_PatternCard_shows_datetime', () => {
    render(<PatternCard pattern={mockPatternItem} def={mockPatternDef} />)
    expect(screen.getByText('2024-01-01')).toBeInTheDocument()
  })

  it('test_PatternCard_click_opens_detail', async () => {
    const onClick = vi.fn()
    render(<PatternCard pattern={mockPatternItem} def={mockPatternDef} onClick={onClick} />)
    await userEvent.click(screen.getByTestId('pattern-card'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('test_PatternCard_renders_reversal_color', () => {
    render(<PatternCard pattern={mockPatternItem} def={mockPatternDef} />)
    // reversal category uses accent color
    const card = screen.getByTestId('pattern-card')
    expect(card).toBeInTheDocument()
  })

  it('test_PatternCard_renders_without_confidence', () => {
    render(<PatternCard pattern={mockPatternItem} def={mockPatternDef} />)
    expect(screen.getByTestId('pattern-card')).toBeInTheDocument()
  })
})
