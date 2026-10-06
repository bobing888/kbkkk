/**
 * PatternCard — 形态玻璃卡片（M3 3.5）
 * V2 §3.5 强制：3 类颜色（reversal=accent / continuation=success / warning=accent）
 * License: Original work for kbkkk project.
 */
import type { FC } from 'react'
import { GlassCard } from '../ui/GlassCard'
import { PATTERN_COLORS, PATTERN_CATEGORY_LABELS, type PatternDef } from '../../constants/patterns'
import type { PatternItem } from '../../types/analysis'

interface PatternCardProps {
  pattern: PatternItem
  def: PatternDef
  onClick?: () => void
  /** 测试 id */
  'data-testid'?: string
}

/** 格式化日期 */
function formatDate(dt: string | undefined): string {
  if (!dt) return '—'
  return dt.slice(0, 10)
}

export const PatternCard: FC<PatternCardProps> = ({
  pattern,
  def,
  onClick,
  'data-testid': testId,
}) => {
  const color = PATTERN_COLORS[def.category]
  const categoryLabel = PATTERN_CATEGORY_LABELS[def.category]
  // confidence 可能在 PatternItem 上（从 API 来），默认 0.8
  const confidence = (pattern as PatternItem & { confidence?: number }).confidence ?? 0.8

  return (
    <GlassCard
      data-testid={testId ?? 'pattern-card'}
      hoverable={!!onClick}
      onClick={onClick}
      padding="sm"
      className="relative overflow-hidden"
    >
      {/* 左侧色条指示类别 */}
      <div
        aria-hidden="true"
        className="absolute left-0 top-0 bottom-0 w-1 rounded-l-kbkkk-lg"
        style={{ backgroundColor: color }}
      />

      <div className="pl-2 flex flex-col gap-2">
        {/* 顶部行：图标 + 名称 + 类别标签 */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span aria-hidden="true" className="text-base flex-shrink-0">{def.icon}</span>
            <span
              className="text-sm font-medium text-kbkkk-text truncate"
              title={def.displayName}
            >
              {def.displayName}
            </span>
          </div>
          <span
            className="text-xs font-semibold px-2 py-0.5 rounded-full flex-shrink-0"
            style={{
              color,
              backgroundColor: `${color}18`,
              border: `1px solid ${color}33`,
            }}
          >
            {categoryLabel}
          </span>
        </div>

        {/* 中间行：置信度条 */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-kbkkk-muted">置信</span>
          <div className="flex-1 h-1.5 rounded-full bg-kbkkk-surface overflow-hidden">
            <div
              aria-hidden="true"
              className="h-full rounded-full transition-all"
              style={{
                width: `${confidence * 100}%`,
                backgroundColor: color,
              }}
            />
          </div>
          <span
            className="text-xs font-semibold tabular-nums"
            style={{ color }}
          >
            {(confidence * 100).toFixed(0)}%
          </span>
        </div>

        {/* 底部行：时间 */}
        <div className="flex items-center justify-end gap-2 text-xs text-kbkkk-muted">
          <span className="tabular-nums">{formatDate(pattern.datetime)}</span>
        </div>
      </div>
    </GlassCard>
  )
}
