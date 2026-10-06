/**
 * SignalCard — 5 类信号玻璃卡片（M3 3.4）
 * V2 §3.4 强制：buy=accent(#f7931a) / sell=danger(#ea3943) / warning=success(#16c784)
 * License: Original work for kbkkk project.
 */
import type { FC } from 'react'
import { GlassCard } from '../ui/GlassCard'
import type { SignalItem } from '../../types/analysis'

interface SignalCardProps {
  signal: SignalItem
  onClick?: () => void
  /** 测试 id */
  'data-testid'?: string
}

// 方向映射
const DIRECTION_LABELS = {
  long: '做多',
  short: '做空',
  neutral: '中性',
} as const

// 方向颜色（对应 V2 §3.2 MARKER_COLORS）
const DIRECTION_COLORS = {
  long: '#f7931a',    // accent — buy
  short: '#ea3943',   // danger — sell
  neutral: '#16c784', // success — warning
} as const

// 方向图标
const DIRECTION_ICONS = {
  long: '📈',
  short: '📉',
  neutral: '⚠️',
} as const

/** 格式化置信度 */
function formatConfidence(c: number): string {
  return `${(c * 100).toFixed(0)}%`
}

/** 格式化价格 */
function formatPrice(p: number | undefined): string {
  if (p === undefined) return '—'
  return p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** 格式化日期 */
function formatDate(dt: string | undefined): string {
  if (!dt) return '—'
  return dt.slice(0, 10)
}

export const SignalCard: FC<SignalCardProps> = ({
  signal,
  onClick,
  'data-testid': testId,
}) => {
  const color = DIRECTION_COLORS[signal.direction]
  const label = DIRECTION_LABELS[signal.direction]
  const icon = DIRECTION_ICONS[signal.direction]

  return (
    <GlassCard
      data-testid={testId ?? 'signal-card'}
      hoverable={!!onClick}
      onClick={onClick}
      padding="sm"
      className="relative overflow-hidden"
    >
      {/* 左侧色条指示方向 */}
      <div
        aria-hidden="true"
        className="absolute left-0 top-0 bottom-0 w-1 rounded-l-kbkkk-lg"
        style={{ backgroundColor: color }}
      />

      <div className="pl-2 flex flex-col gap-2">
        {/* 顶部行：图标 + 名称 + 方向标签 */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span aria-hidden="true" className="text-base flex-shrink-0">{icon}</span>
            <span
              className="text-sm font-medium text-kbkkk-text truncate"
              title={signal.name}
            >
              {signal.name}
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
            {label}
          </span>
        </div>

        {/* 中间行：置信度 + 来源 */}
        <div className="flex items-center justify-between gap-2">
          {/* 置信度条 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-kbkkk-muted">置信</span>
            <div className="w-24 h-1.5 rounded-full bg-kbkkk-surface overflow-hidden">
              <div
                aria-hidden="true"
                className="h-full rounded-full transition-all"
                style={{
                  width: `${signal.confidence * 100}%`,
                  backgroundColor: color,
                }}
              />
            </div>
            <span
              className="text-xs font-semibold tabular-nums"
              style={{ color }}
            >
              {formatConfidence(signal.confidence)}
            </span>
          </div>
          {/* 来源标签 */}
          {signal.sources.length > 0 && (
            <div className="flex gap-1 flex-wrap justify-end">
              {signal.sources.slice(0, 3).map((s) => (
                <span
                  key={s}
                  className="text-xs px-1.5 py-0.5 rounded bg-kbkkk-surface text-kbkkk-muted"
                >
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* 底部行：价格信息 + 时间戳 */}
        <div className="flex items-center justify-between gap-2 text-xs text-kbkkk-muted">
          <div className="flex items-center gap-3">
            {signal.entry !== undefined && (
              <span title="入场价">
                入 <span className="text-kbkkk-text font-medium tabular-nums">{formatPrice(signal.entry)}</span>
              </span>
            )}
            {signal.stop_loss !== undefined && (
              <span title="止损" className="text-kbkkk-danger">
                损 <span className="tabular-nums">{formatPrice(signal.stop_loss)}</span>
              </span>
            )}
            {signal.take_profit !== undefined && (
              <span title="止盈" className="text-kbkkk-success">
                盈 <span className="tabular-nums">{formatPrice(signal.take_profit)}</span>
              </span>
            )}
          </div>
          <span className="tabular-nums">{formatDate(signal.datetime)}</span>
        </div>
      </div>
    </GlassCard>
  )
}
