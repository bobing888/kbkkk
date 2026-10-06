/**
 * Zustand stores tests — 全局状态管理
 * M3 3.1: useUIStore / useSymbolStore / useKlineStore
 *
 * TDD 铁律：先红后绿
 * - test_useUIStore_default_theme_is_dark
 * - test_useSymbolStore_default_btc_eth
 * - test_useKlineStore_initial_state
 */
import { describe, it, expect } from 'vitest'
import { useUIStore, useSymbolStore, useKlineStore } from '../store'

describe('useUIStore — 外观状态', () => {
  it('默认主题是 dark', () => {
    // 每个测试用独立的 getState() 确保隔离
    const state = useUIStore.getState()
    expect(state.theme).toBe('dark')
  })

  it('默认 sidebar 是关闭的', () => {
    const state = useUIStore.getState()
    expect(state.sidebarOpen).toBe(false)
  })
})

describe('useSymbolStore — 标的选择状态', () => {
  it('默认 symbol 是 BTC', () => {
    const state = useSymbolStore.getState()
    expect(state.symbol).toBe('BTC')
  })

  it('默认 market 是 crypto', () => {
    const state = useSymbolStore.getState()
    expect(state.market).toBe('crypto')
  })
})

describe('useKlineStore — K线数据缓存', () => {
  it('初始状态 loading=false error=null data=undefined', () => {
    const state = useKlineStore.getState()
    expect(state.loading).toBe(false)
    expect(state.error).toBe(null)
    expect(state.data).toBeUndefined()
  })
})
