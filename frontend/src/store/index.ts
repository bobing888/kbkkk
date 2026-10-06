/**
 * Zustand global stores — 全局状态管理
 * M3 3.1: useUIStore / useSymbolStore / useKlineStore
 * 使用 zustand v5 create() 写法 + TypeScript 严格类型
 */
import { create } from 'zustand'
import type { Period, Market } from '../api/klineApi'
import type { KLineData } from '../types/kline'

// ─── useUIStore — 外观/侧边栏状态 ───────────────────────────────────────

export type Theme = 'dark' | 'light' | 'system'

interface UIState {
  theme: Theme
  sidebarOpen: boolean
  preferences: Record<string, unknown>
}

interface UIActions {
  setTheme: (theme: Theme) => void
  setSidebarOpen: (open: boolean) => void
  toggleSidebar: () => void
  setPreference: (key: string, value: unknown) => void
}

export type UIStore = UIState & UIActions

export const useUIStore = create<UIStore>((set) => ({
  // 暗色强制（V2 §3.0 不变量）
  theme: 'dark',
  sidebarOpen: false,
  preferences: {},

  setTheme: (theme) => set({ theme }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setPreference: (key, value) =>
    set((s) => ({ preferences: { ...s.preferences, [key]: value } })),
}))

// ─── useSymbolStore — 标的选择状态 ────────────────────────────────────────

interface SymbolState {
  symbol: string
  period: Period
  market: Market
}

interface SymbolActions {
  setSymbol: (symbol: string) => void
  setPeriod: (period: Period) => void
  setMarket: (market: Market) => void
}

export type SymbolStore = SymbolState & SymbolActions

export const useSymbolStore = create<SymbolStore>((set) => ({
  // BTC/ETH 默认（V2 §1 强制）
  symbol: 'BTC',
  period: '1d',
  market: 'crypto',

  setSymbol: (symbol) => set({ symbol }),
  setPeriod: (period) => set({ period }),
  setMarket: (market) => set({ market }),
}))

// ─── useKlineStore — K线数据缓存 ────────────────────────────────────────

interface KlineState {
  data: KLineData[] | undefined
  loading: boolean
  error: string | null
  lastUpdated: Date | null
}

interface KlineActions {
  setData: (data: KLineData[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setLastUpdated: (date: Date) => void
  reset: () => void
}

export type KlineStore = KlineState & KlineActions

export const useKlineStore = create<KlineStore>((set) => ({
  data: undefined,
  loading: false,
  error: null,
  lastUpdated: null,

  setData: (data) => set({ data }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  setLastUpdated: (date) => set({ lastUpdated: date }),
  reset: () => set({ data: undefined, loading: false, error: null, lastUpdated: null }),
}))
