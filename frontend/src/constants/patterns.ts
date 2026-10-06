/**
 * Patterns constants — M3 3.5
 * V2 §3.5 强制：11 种 K 线形态（3 反转 + 3 持续 + 3 中继 + 2 警告）
 * License: Original work for kbkkk project.
 */

/** 形态类别 */
export type PatternCategory = 'reversal' | 'continuation' | 'midline' | 'warning'

/** 单个形态定义 */
export interface PatternDef {
  name: string
  displayName: string
  category: PatternCategory
  description: string
  icon: string
}

/** 11 种 K 线形态定义（V2 §3.5 强制）*/
export const PATTERNS: PatternDef[] = [
  // ── 3 反转 ────────────────────────────────────────────────
  {
    name: 'HEAD_AND_SHOULDERS_TOP',
    displayName: '头肩顶',
    category: 'reversal',
    description: '看跌反转形态，由三个峰值组成，中间峰值最高。',
    icon: '👕',
  },
  {
    name: 'DOUBLE_TOP',
    displayName: '双顶',
    category: 'reversal',
    description: '看跌反转形态，价格两次触及相近高点后下跌。',
    icon: '⏳',
  },
  {
    name: 'V_SHAPE',
    displayName: 'V 形反转',
    category: 'reversal',
    description: '快速下跌后快速反弹的 V 形反转。',
    icon: '⚡',
  },

  // ── 3 持续 ────────────────────────────────────────────────
  {
    name: 'ASCENDING_TRIANGLE',
    displayName: '上升三角形',
    category: 'continuation',
    description: '看涨持续形态，水平上阻力线 + 上升趋势支撑线。',
    icon: '📈',
  },
  {
    name: 'DESCENDING_TRIANGLE',
    displayName: '下降三角形',
    category: 'continuation',
    description: '看跌持续形态，水平下支撑线 + 下降趋势阻力线。',
    icon: '📉',
  },
  {
    name: 'RECTANGLE',
    displayName: '矩形整理',
    category: 'continuation',
    description: '价格在平行支撑阻力之间震荡整理。',
    icon: '🟧',
  },

  // ── 3 中继 ────────────────────────────────────────────────
  {
    name: 'BULL_FLAG',
    displayName: '牛市旗形',
    category: 'midline',
    description: '上涨后短暂回调的旗形中继形态。',
    icon: '🚩',
  },
  {
    name: 'BEAR_FLAG',
    displayName: '熊市旗形',
    category: 'midline',
    description: '下跌后短暂反弹的倒旗形中继形态。',
    icon: '🚩',
  },
  {
    name: 'WEDGE',
    displayName: '楔形',
    category: 'midline',
    description: '收敛三角形中继形态，上升或下降楔形。',
    icon: '🔺',
  },

  // ── 2 警告 ────────────────────────────────────────────────
  {
    name: 'BULLISH_ENGULFING',
    displayName: '看涨吞没',
    category: 'warning',
    description: '看涨反转信号，阴线后阳线完全吞没前一根。',
    icon: '🐂',
  },
  {
    name: 'BEARISH_ENGULFING',
    displayName: '看跌吞没',
    category: 'warning',
    description: '看跌反转信号，阳线后阴线完全吞没前一根。',
    icon: '🐻',
  },
] // 11 种：3 反转 + 3 持续 + 3 中继 + 2 警告

/** 形态名称 → PatternDef 映射 */
export const PATTERN_MAP: Record<string, PatternDef> = Object.fromEntries(
  PATTERNS.map((p) => [p.name, p])
)

/** 形态类别 → 颜色映射 */
export const PATTERN_COLORS: Record<PatternCategory, string> = {
  reversal: '#f7931a',      // accent — BTC orange
  continuation: '#16c784',   // success — crypto green
  midline: '#16c784',        // success
  warning: '#f7931a',       // accent
}

/** 形态类别 → 中文标签映射 */
export const PATTERN_CATEGORY_LABELS: Record<PatternCategory, string> = {
  reversal: '反转',
  continuation: '持续',
  midline: '中继',
  warning: '警告',
}

/** 类别过滤选项 */
export const PATTERN_FILTER_OPTIONS: { label: string; value: PatternCategory | 'all' }[] = [
  { label: '全部', value: 'all' },
  { label: '反转', value: 'reversal' },
  { label: '持续', value: 'continuation' },
  { label: '中继', value: 'midline' },
  { label: '警告', value: 'warning' },
]
