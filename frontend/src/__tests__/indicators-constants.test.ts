/**
 * 指标常量测试 — V2 §3.3 + §10 #1 强制
 * 覆盖：分类 / 数量 / 默认启用 / 命名规范
 */
import { describe, it, expect } from 'vitest'
import {
  INDICATORS,
  INDICATOR_MAP,
  CORE_INDICATORS,
  ADVANCED_INDICATORS,
  RESERVED_INDICATORS,
  ALL_INDICATOR_NAMES,
  DEFAULT_ENABLED_INDICATORS,
} from '../constants/indicators'

describe('indicators — 11 指标常量', () => {
  it('test_indicators_has_4_core_categories', () => {
    const core = INDICATORS.filter((ind) => ind.category === 'core')
    expect(core).toHaveLength(4)
    expect(core.map((ind) => ind.name)).toEqual(['MA', 'EMA', 'MACD', 'KDJ'])
  })

  it('test_indicators_has_5_advanced_categories', () => {
    const advanced = INDICATORS.filter((ind) => ind.category === 'advanced')
    expect(advanced).toHaveLength(5)
    expect(advanced.map((ind) => ind.name)).toEqual(['BOLL', 'RSI', 'ATR', 'OBV', 'VWAP'])
  })

  it('test_indicators_has_2_reserved_categories', () => {
    const reserved = INDICATORS.filter((ind) => ind.category === 'reserved')
    expect(reserved).toHaveLength(2)
    expect(reserved.map((ind) => ind.name)).toEqual(['CCI', 'WR'])
  })

  it('test_indicators_default_enabled_is_4_core', () => {
    const defaults = INDICATORS.filter((ind) => ind.defaultEnabled)
    expect(defaults).toHaveLength(4)
    expect(defaults.map((ind) => ind.name)).toEqual(['MA', 'EMA', 'MACD', 'KDJ'])
  })

  it('test_indicators_names_are_upper_snake_case', () => {
    for (const ind of INDICATORS) {
      expect(ind.name).toMatch(/^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$/)
    }
  })

  it('test_indicators_total_is_11', () => {
    expect(INDICATORS).toHaveLength(11)
  })

  it('test_indicators_map_has_all_names', () => {
    expect(Object.keys(INDICATOR_MAP)).toHaveLength(11)
    for (const name of ALL_INDICATOR_NAMES) {
      expect(INDICATOR_MAP[name]).toBeDefined()
    }
  })

  it('test_default_enabled_indicators_exports_correct_list', () => {
    expect(DEFAULT_ENABLED_INDICATORS).toEqual(['MA', 'EMA', 'MACD', 'KDJ'])
  })

  it('test_core_indicators_exports_4_names', () => {
    expect(CORE_INDICATORS).toHaveLength(4)
  })

  it('test_advanced_indicators_exports_5_names', () => {
    expect(ADVANCED_INDICATORS).toHaveLength(5)
  })

  it('test_reserved_indicators_exports_2_names', () => {
    expect(RESERVED_INDICATORS).toHaveLength(2)
  })

  it('test_indicators_have_display_names', () => {
    for (const ind of INDICATORS) {
      expect(ind.displayName.length).toBeGreaterThan(0)
    }
  })

  it('test_indicators_have_descriptions', () => {
    for (const ind of INDICATORS) {
      expect(ind.description.length).toBeGreaterThan(0)
    }
  })

  it('test_indicators_have_format_config', () => {
    for (const ind of INDICATORS) {
      expect(ind.format).toBeDefined()
      expect(typeof ind.format.decimalPlaces).toBe('number')
      expect(typeof ind.format.isPercent).toBe('boolean')
    }
  })

  it('test_rsi_is_percent_format', () => {
    const rsi = INDICATOR_MAP['RSI']
    expect(rsi.format.isPercent).toBe(true)
  })

  it('test_macd_kdj_use_4_decimal_places', () => {
    expect(INDICATOR_MAP['MACD'].format.decimalPlaces).toBe(4)
    expect(INDICATOR_MAP['KDJ'].format.decimalPlaces).toBe(4)
  })
})
