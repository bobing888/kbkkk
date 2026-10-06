/**
 * Pattern constants tests — M3 3.5
 * TDD 铁律：先写失败测试
 * License: Original work for kbkkk project.
 */
import { describe, it, expect } from 'vitest'
import {
  PATTERNS,
  PATTERN_MAP,
  PATTERN_COLORS,
  PATTERN_CATEGORY_LABELS,
  PATTERN_FILTER_OPTIONS,
} from '../constants/patterns'

describe('patterns constants — M3 3.5', () => {
  it('test_patterns_has_11_total', () => {
    // 3 反转 + 3 持续 + 3 中继 + 2 警告 = 11
    expect(PATTERNS).toHaveLength(11)
  })

  it('test_patterns_has_3_reversal_categories', () => {
    const reversals = PATTERNS.filter((p) => p.category === 'reversal')
    expect(reversals).toHaveLength(3)
  })

  it('test_patterns_has_3_continuation_categories', () => {
    const continuations = PATTERNS.filter((p) => p.category === 'continuation')
    expect(continuations).toHaveLength(3)
  })

  it('test_patterns_has_3_midline_categories', () => {
    const midlines = PATTERNS.filter((p) => p.category === 'midline')
    expect(midlines).toHaveLength(3)
  })

  it('test_patterns_has_2_warning_categories', () => {
    const warnings = PATTERNS.filter((p) => p.category === 'warning')
    expect(warnings).toHaveLength(2)
  })

  it('test_patterns_names_are_upper_snake_case', () => {
    for (const p of PATTERNS) {
      expect(p.name).toMatch(/^[A-Z][A-Z0-9_]+$/)
    }
  })

  it('test_patterns_icons_exist', () => {
    for (const p of PATTERNS) {
      expect(typeof p.icon).toBe('string')
      expect(p.icon.length).toBeGreaterThan(0)
    }
  })

  it('test_pattern_map_keys_match_names', () => {
    for (const p of PATTERNS) {
      expect(PATTERN_MAP[p.name]).toBeDefined()
      expect(PATTERN_MAP[p.name].displayName).toBe(p.displayName)
    }
  })

  it('test_pattern_colors_has_all_categories', () => {
    expect(PATTERN_COLORS.reversal).toBe('#f7931a')
    expect(PATTERN_COLORS.continuation).toBe('#16c784')
    expect(PATTERN_COLORS.midline).toBe('#16c784')
    expect(PATTERN_COLORS.warning).toBe('#f7931a')
  })

  it('test_pattern_category_labels_has_all', () => {
    expect(PATTERN_CATEGORY_LABELS.reversal).toBe('反转')
    expect(PATTERN_CATEGORY_LABELS.continuation).toBe('持续')
    expect(PATTERN_CATEGORY_LABELS.midline).toBe('中继')
    expect(PATTERN_CATEGORY_LABELS.warning).toBe('警告')
  })

  it('test_pattern_filter_options_includes_all', () => {
    const labels = PATTERN_FILTER_OPTIONS.map((o) => o.value)
    expect(labels).toContain('all')
    expect(labels).toContain('reversal')
    expect(labels).toContain('continuation')
    expect(labels).toContain('midline')
    expect(labels).toContain('warning')
  })

  it('test_patterns_have_descriptions', () => {
    for (const p of PATTERNS) {
      expect(typeof p.description).toBe('string')
      expect(p.description.length).toBeGreaterThan(0)
    }
  })

  it('test_patterns_have_display_names', () => {
    for (const p of PATTERNS) {
      expect(typeof p.displayName).toBe('string')
      expect(p.displayName.length).toBeGreaterThan(0)
    }
  })
})
