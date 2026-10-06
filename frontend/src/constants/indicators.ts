/**
 * 11 指标常量定义（V2 §3.3 强制）
 * 4 核心 + 5 高级 + 2 高级预留
 *
 * License: MIT
 */

/** 指标分类 */
export type IndicatorCategory = 'core' | 'advanced' | 'reserved'

/** 单个指标定义 */
export interface IndicatorDefinition {
  /** 指标名称（UPPER_SNAKE_CASE）*/
  name: string
  /** 显示名称 */
  displayName: string
  /** 分类 */
  category: IndicatorCategory
  /** 描述 */
  description: string
  /** 默认启用（4 核心）*/
  defaultEnabled: boolean
  /** 数值精度：decimal=小数位，percent=是否显示% */
  format: {
    decimalPlaces: number
    isPercent: boolean
  }
}

/** 11 指标定义 */
export const INDICATORS: IndicatorDefinition[] = [
  // ─── 4 核心指标（默认启用）──────────────────────────────────────────────
  {
    name: 'MA',
    displayName: '均线 (MA)',
    category: 'core',
    description: '简单移动平均线，5/10/20/60 周期',
    defaultEnabled: true,
    format: { decimalPlaces: 2, isPercent: false },
  },
  {
    name: 'EMA',
    displayName: '指数移动平均 (EMA)',
    category: 'core',
    description: '指数加权移动平均，反应更灵敏',
    defaultEnabled: true,
    format: { decimalPlaces: 2, isPercent: false },
  },
  {
    name: 'MACD',
    displayName: 'MACD',
    category: 'core',
    description: '异同移动平均线，DIF/DEA/MACD 三线',
    defaultEnabled: true,
    format: { decimalPlaces: 4, isPercent: false },
  },
  {
    name: 'KDJ',
    displayName: '随机指标 (KDJ)',
    category: 'core',
    description: '随机指标，K/D/J 三值超买超卖',
    defaultEnabled: true,
    format: { decimalPlaces: 4, isPercent: false },
  },

  // ─── 5 高级指标──────────────────────────────────────────────────────────
  {
    name: 'BOLL',
    displayName: '布林带 (BOLL)',
    category: 'advanced',
    description: '中轨 ± 2 倍标准差，上下轨通道',
    defaultEnabled: false,
    format: { decimalPlaces: 2, isPercent: false },
  },
  {
    name: 'RSI',
    displayName: '相对强弱 (RSI)',
    category: 'advanced',
    description: '0-100 超买超卖指标，14 周期',
    defaultEnabled: false,
    format: { decimalPlaces: 2, isPercent: true },
  },
  {
    name: 'ATR',
    displayName: '平均真实波幅 (ATR)',
    category: 'advanced',
    description: '平均真实波幅，衡量波动率',
    defaultEnabled: false,
    format: { decimalPlaces: 2, isPercent: false },
  },
  {
    name: 'OBV',
    displayName: '能量潮 (OBV)',
    category: 'advanced',
    description: '成交量累积，趋势确认指标',
    defaultEnabled: false,
    format: { decimalPlaces: 2, isPercent: false },
  },
  {
    name: 'VWAP',
    displayName: '成交量加权均价 (VWAP)',
    category: 'advanced',
    description: '当日平均成交价，机构参考',
    defaultEnabled: false,
    format: { decimalPlaces: 2, isPercent: false },
  },

  // ─── 2 高级预留指标──────────────────────────────────────────────────────
  {
    name: 'CCI',
    displayName: '顺势指标 (CCI)',
    category: 'reserved',
    description: '商品通道指标，衡量价格偏离均值程度',
    defaultEnabled: false,
    format: { decimalPlaces: 2, isPercent: false },
  },
  {
    name: 'WR',
    displayName: '威廉指标 (WR)',
    category: 'reserved',
    description: '-100~0 超买超卖，14 周期',
    defaultEnabled: false,
    format: { decimalPlaces: 2, isPercent: false },
  },
]

/** 按名称快速查找 */
export const INDICATOR_MAP = Object.fromEntries(
  INDICATORS.map((ind) => [ind.name, ind])
) as Record<string, IndicatorDefinition>

/** 4 核心指标名称列表 */
export const CORE_INDICATORS = INDICATORS.filter(
  (ind) => ind.category === 'core'
).map((ind) => ind.name)

/** 5 高级指标名称列表 */
export const ADVANCED_INDICATORS = INDICATORS.filter(
  (ind) => ind.category === 'advanced'
).map((ind) => ind.name)

/** 2 预留指标名称列表 */
export const RESERVED_INDICATORS = INDICATORS.filter(
  (ind) => ind.category === 'reserved'
).map((ind) => ind.name)

/** 所有指标名称列表 */
export const ALL_INDICATOR_NAMES = INDICATORS.map((ind) => ind.name)

/** 默认启用的指标（4 核心）*/
export const DEFAULT_ENABLED_INDICATORS = INDICATORS.filter(
  (ind) => ind.defaultEnabled
).map((ind) => ind.name)
