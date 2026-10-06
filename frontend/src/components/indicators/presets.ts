/**
 * 指标预设工具（M3 3.3）
 * 快速切换不同分析场景的指标组合
 */

/** 核心组合：趋势 + 动量 */
export const CORE_PRESET = ['MA', 'EMA', 'MACD', 'KDJ'] as const

/** 趋势组合：均线 + 通道 + 均价 */
export const TREND_PRESET = ['MA', 'EMA', 'BOLL', 'VWAP'] as const

/** 摆动组合：超买超卖指标 */
export const OSCILLATOR_PRESET = ['RSI', 'KDJ', 'CCI', 'WR'] as const

/** 成交量组合：量价分析 */
export const VOLUME_PRESET = ['OBV', 'VWAP'] as const

/** 所有预设（用于 UI 选择）*/
export const PRESET_OPTIONS = [
  { value: 'core', label: '核心组合', indicators: CORE_PRESET },
  { value: 'trend', label: '趋势组合', indicators: TREND_PRESET },
  { value: 'oscillator', label: '摆动组合', indicators: OSCILLATOR_PRESET },
  { value: 'volume', label: '成交量组合', indicators: VOLUME_PRESET },
] as const

/** 预设类型 */
export type PresetKey = (typeof PRESET_OPTIONS)[number]['value']
