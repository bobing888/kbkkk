/**
 * Markers 工具函数 — M3 3.2
 * V2 §3.2 强制：5 类 markers（buy / sell / warning / pattern-up / pattern-down）
 * V2 §10 #8：markers 必须接通 patterns + signals
 * License: Original work for kbkkk project.
 */
import type { PatternItem } from '../../types/analysis'
import type { SignalItem } from '../../types/analysis'

/** lightweight-charts MarkerShape */
export type MarkerShape = 'arrowUp' | 'arrowDown' | 'circle' | 'square'

export interface MarkerData {
  time: string
  position: 'aboveBar' | 'belowBar'
  color: string
  shape: MarkerShape
  text: string
}

// V2 §3.2 marker 颜色定义（用 tokens）
const MARKER_COLORS = {
  buy: '#f7931a',         // accent — BTC orange
  sell: '#ea3943',         // danger — crypto red
  warning: '#16c784',      // success — warning 用绿色
  patternUp: '#f7931a',    // accent
  patternDown: '#ea3943',  // danger
} as const

/** 判断 pattern 是否为 bullish */
function isBullishPattern(name: string): boolean {
  const bullish = ['hammer', 'hammer_inverted', 'engulfing_bull', 'morning_star', 'piercing', 'three_white_soldiers']
  return bullish.includes(name.toLowerCase())
}

/** 从 SignalItem 提取 datetime */
function signalTime(s: SignalItem): string {
  if (s.datetime) return s.datetime.slice(0, 10)
  return ''
}

/** 从 PatternItem 提取 datetime */
function patternTime(p: PatternItem): string {
  return p.datetime.slice(0, 10)
}

/**
 * 从 patterns + signals 生成 lightweight-charts markers。
 * - long signal → buy marker（belowBar, B）
 * - short signal → sell marker（aboveBar, S）
 * - neutral signal with low confidence → warning marker（belowBar, !）
 * - bullish pattern → pattern-up marker（belowBar, ↑）
 * - bearish pattern → pattern-down marker（aboveBar, ↓）
 * - 同一根 K 线最多 3 个 marker
 */
export function createMarkers(
  patterns: PatternItem[],
  signals: SignalItem[],
): MarkerData[] {
  const markerMap = new Map<string, MarkerData[]>()

  // 从 signals 生成 markers
  for (const sig of signals) {
    const time = signalTime(sig)
    if (!time) continue

    const existing = markerMap.get(time) ?? []
    if (existing.length >= 3) continue // 同根 K 线最多 3 个

    if (sig.direction === 'long') {
      existing.push({
        time,
        position: 'belowBar',
        color: MARKER_COLORS.buy,
        shape: 'arrowUp',
        text: 'B',
      })
    } else if (sig.direction === 'short') {
      existing.push({
        time,
        position: 'aboveBar',
        color: MARKER_COLORS.sell,
        shape: 'arrowDown',
        text: 'S',
      })
    } else if (sig.direction === 'neutral' && sig.confidence < 0.6) {
      // low confidence neutral → warning
      existing.push({
        time,
        position: 'belowBar',
        color: MARKER_COLORS.warning,
        shape: 'circle',
        text: '!',
      })
    }
    markerMap.set(time, existing)
  }

  // 从 patterns 生成 markers
  for (const pat of patterns) {
    const time = patternTime(pat)
    if (!time) continue

    const existing = markerMap.get(time) ?? []
    if (existing.length >= 3) continue

    if (isBullishPattern(pat.name)) {
      existing.push({
        time,
        position: 'belowBar',
        color: MARKER_COLORS.patternUp,
        shape: 'arrowUp',
        text: '↑',
      })
    } else {
      existing.push({
        time,
        position: 'aboveBar',
        color: MARKER_COLORS.patternDown,
        shape: 'arrowDown',
        text: '↓',
      })
    }
    markerMap.set(time, existing)
  }

  // 合并并按 time 升序排序
  const allMarkers = Array.from(markerMap.values()).flat()
  return allMarkers.sort((a, b) => a.time.localeCompare(b.time))
}
