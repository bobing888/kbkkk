/**
 * Markers 工具函数测试 — M3 3.2
 * V2 §3.2 强制：5 类 markers（buy / sell / warning / pattern-up / pattern-down）
 * V2 §10 #8：markers 必须接通 patterns + signals
 */
import { describe, it, expect } from 'vitest'
import { createMarkers, type MarkerData } from '../components/KLineChart/markers'
import type { PatternItem } from '../types/analysis'
import type { SignalItem } from '../types/analysis'

// ─── Mock data ─────────────────────────────────────────────────────────────

const mockPatterns: PatternItem[] = [
  { datetime: '2024-01-01T00:00:00', name: 'hammer', open: 42000, high: 42500, low: 41800, close: 42300 },
  { datetime: '2024-01-02T00:00:00', name: 'doji', open: 42300, high: 43000, low: 42100, close: 42800 },
]

const mockSignals: SignalItem[] = [
  { name: 'MA Cross', direction: 'long', confidence: 0.82, sources: ['MA5', 'MA10'] },
  { name: 'RSI Oversold', direction: 'short', confidence: 0.65, sources: ['RSI'] },
  { name: 'Volume Spike', direction: 'long', confidence: 0.55, sources: ['OBV'] },
]

// ─── Tests ─────────────────────────────────────────────────────────────────

describe('markers.ts — M3 3.2 5 类 markers', () => {
  // ── V2 §3.2: buy signal → buy marker ─────────────────────────────────
  it('test_createMarkers_converts_buy_signal_to_marker', () => {
    const longSignal: SignalItem = {
      name: 'MA Cross',
      direction: 'long',
      confidence: 0.82,
      sources: ['MA5', 'MA10'],
      datetime: '2024-01-01T00:00:00',
    }
    const markers = createMarkers(mockPatterns, [longSignal])

    const buyMarker = markers.find((m) => m.color === '#f7931a' && m.shape === 'arrowUp')
    expect(buyMarker).toBeDefined()
    expect(buyMarker?.text).toBe('B')
    expect(buyMarker?.position).toBe('belowBar')
  })

  // ── V2 §3.2: sell signal → sell marker ───────────────────────────────
  it('test_createMarkers_converts_sell_signal_to_marker', () => {
    const shortSignal: SignalItem = {
      name: 'RSI Overbought',
      direction: 'short',
      confidence: 0.75,
      sources: ['RSI'],
      datetime: '2024-01-02T00:00:00',
    }
    const markers = createMarkers(mockPatterns, [shortSignal])

    const sellMarker = markers.find((m) => m.color === '#ea3943' && m.shape === 'arrowDown')
    expect(sellMarker).toBeDefined()
    expect(sellMarker?.text).toBe('S')
    expect(sellMarker?.position).toBe('aboveBar')
  })

  // ── V2 §3.2: pattern-up → pattern-up marker ─────────────────────────
  it('test_createMarkers_converts_pattern_to_marker', () => {
    const bullishPattern: PatternItem = {
      datetime: '2024-01-01T00:00:00',
      name: 'hammer',
      open: 42000,
      high: 42500,
      low: 41800,
      close: 42300,
    }
    const markers = createMarkers([bullishPattern], [])

    const patternMarker = markers.find((m) => m.color === '#f7931a' && m.shape === 'arrowUp')
    expect(patternMarker).toBeDefined()
    expect(patternMarker?.text).toBe('↑')
    expect(patternMarker?.position).toBe('belowBar')
  })

  // ── V2 §3.2: pattern-down → pattern-down marker ─────────────────────
  it('test_createMarkers_converts_pattern_down_to_marker', () => {
    const bearishPattern: PatternItem = {
      datetime: '2024-01-03T00:00:00',
      name: 'shooting_star',
      open: 43000,
      high: 43500,
      low: 42800,
      close: 42900,
    }
    const markers = createMarkers([bearishPattern], [])

    const patternDownMarker = markers.find((m) => m.color === '#ea3943' && m.shape === 'arrowDown')
    expect(patternDownMarker).toBeDefined()
    expect(patternDownMarker?.text).toBe('↓')
    expect(patternDownMarker?.position).toBe('aboveBar')
  })

  // ── V2 §3.2: warning marker (neutral signal) ─────────────────────────
  it('test_createMarkers_converts_warning_signal_to_marker', () => {
    const warningSignal: SignalItem = {
      name: 'Low Confidence',
      direction: 'neutral',
      confidence: 0.45,
      sources: ['RSI'],
      datetime: '2024-01-01T00:00:00',
    }
    const markers = createMarkers([], [warningSignal])

    const warningMarker = markers.find((m) => m.color === '#16c784')
    expect(warningMarker).toBeDefined()
    expect(warningMarker?.text).toBe('!')
    expect(warningMarker?.position).toBe('belowBar')
  })

  // ── V2 §3.2: dedup overlapping markers (max 3 per candle) ─────────────
  it('test_createMarkers_dedup_overlapping_markers', () => {
    // 同一根 K 线生成多个 long signal → 应该去重
    const duplicateSignals: SignalItem[] = [
      { name: 'MA Cross', direction: 'long', confidence: 0.82, sources: ['MA5'], datetime: '2024-01-01T00:00:00' },
      { name: 'MACD Cross', direction: 'long', confidence: 0.78, sources: ['MACD'], datetime: '2024-01-01T00:00:00' },
      { name: 'KDJ Golden', direction: 'long', confidence: 0.85, sources: ['KDJ'], datetime: '2024-01-01T00:00:00' },
      { name: 'Extra Long 1', direction: 'long', confidence: 0.60, sources: ['RSI'], datetime: '2024-01-01T00:00:00' },
      { name: 'Extra Long 2', direction: 'long', confidence: 0.58, sources: ['OBV'], datetime: '2024-01-01T00:00:00' },
    ]
    const markers = createMarkers([], duplicateSignals)

    // 同一天最多 3 个 marker
    const sameDayMarkers = markers.filter((m) => m.time === '2024-01-01')
    expect(sameDayMarkers.length).toBeLessThanOrEqual(3)
  })

  // ── Sort by time ascending ──────────────────────────────────────────────
  it('test_createMarkers_sorts_by_time_asc', () => {
    const markers = createMarkers(mockPatterns, mockSignals)
    if (markers.length < 2) return

    const times = markers.map((m) => m.time)
    const sortedTimes = [...times].sort()
    expect(times).toEqual(sortedTimes)
  })

  // ── Empty inputs → empty array ─────────────────────────────────────────
  it('test_createMarkers_returns_empty_for_no_inputs', () => {
    const markers = createMarkers([], [])
    expect(markers).toEqual([])
  })
})
