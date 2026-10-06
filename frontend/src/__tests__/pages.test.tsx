/**
 * Pages render tests — 3 页面骨架
 * M3 3.1: HomePage / SignalsPage / SettingsPage
 *
 * TDD 铁律：先红后绿
 * - test_HomePage_renders_symbol_selector
 * - test_SignalsPage_renders_placeholder
 * - test_SettingsPage_renders_about_section
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HomePage } from '../pages/HomePage'
import { SignalsPage } from '../pages/SignalsPage'
import { SettingsPage } from '../pages/SettingsPage'

describe('HomePage — 首页（K线 + 指标总览）', () => {
  it('渲染 symbol 选择器', () => {
    render(<HomePage />)
    expect(screen.getByTestId('home-page')).toBeInTheDocument()
    // 有 BTC 按钮
    expect(screen.getByText('BTC')).toBeInTheDocument()
    expect(screen.getByText('ETH')).toBeInTheDocument()
  })
})

describe('SignalsPage — 信号中心', () => {
  it('渲染信号页内容', () => {
    render(<SignalsPage />)
    expect(screen.getByTestId('signals-page')).toBeInTheDocument()
    // 精确匹配页面标题（不是占位符文本）
    expect(screen.getByRole('heading', { name: /信号中心/ })).toBeInTheDocument()
  })
})

describe('SettingsPage — 设置页', () => {
  it('渲染关于区块', () => {
    render(<SettingsPage />)
    expect(screen.getByTestId('settings-page')).toBeInTheDocument()
    expect(screen.getByText(/关于/)).toBeInTheDocument()
  })
})
