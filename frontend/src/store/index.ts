/**
 * Zustand global stores — 全局状态管理
 * M3 3.1: useUIStore / useSymbolStore / useKlineStore
 * M3 3.4: useSignalsStore（实时 WebSocket 信号）
 * 使用 zustand v5 create() 写法 + TypeScript 严格类型
 */
import { create } from 'zustand'
import type { Period, Market } from '../api/klineApi'
import type { KLineData } from '../types/kline'
import type { SignalItem } from '../types/analysis'
import { DEFAULT_ENABLED_INDICATORS, ALL_INDICATOR_NAMES } from '../constants/indicators'

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

// ─── useIndicatorsStore — 指标启停状态 ─────────────────────────────────────

interface IndicatorsState {
  enabledIndicators: string[]
}

interface IndicatorsActions {
  toggle: (name: string) => void
  reset: () => void
  setEnabled: (names: string[]) => void
}

export type IndicatorsStore = IndicatorsState & IndicatorsActions

export const useIndicatorsStore = create<IndicatorsStore>((set) => ({
  // 4 核心默认（V2 §3.3 强制）
  enabledIndicators: [...DEFAULT_ENABLED_INDICATORS],

  toggle: (name: string) =>
    set((s) => ({
      enabledIndicators: s.enabledIndicators.includes(name)
        ? s.enabledIndicators.filter((n) => n !== name)
        : [...s.enabledIndicators, name],
    })),

  reset: () => set({ enabledIndicators: [...DEFAULT_ENABLED_INDICATORS] }),

  setEnabled: (names: string[]) =>
    set({ enabledIndicators: names.filter((n) => ALL_INDICATOR_NAMES.includes(n)) }),
}))

// ─── useSignalsStore — 实时信号流（M3 3.4）─────────────────────────────────
// V2 §3.4：WebSocket 接收信号后 addSignal 到此 store

interface SignalsState {
  signals: SignalItem[]
  lastUpdated: number | null
}

interface SignalsActions {
  addSignal: (signal: SignalItem) => void
  clear: () => void
}

export type SignalsStore = SignalsState & SignalsActions

export const useSignalsStore = create<SignalsStore>((set) => ({
  signals: [],
  lastUpdated: null,

  addSignal: (signal: SignalItem) =>
    set((s) => {
      // 同一 datetime + name 的信号去重
      const exists = s.signals.some(
        (ex) => ex.datetime === signal.datetime && ex.name === signal.name
      )
      if (exists) return s

      const next = [signal, ...s.signals]
      // 最多保留 100 条
      if (next.length > 100) next.length = 100
      return { signals: next, lastUpdated: Date.now() }
    }),

  clear: () => set({ signals: [], lastUpdated: null }),
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
