/**
 * IndicatorCard — 单指标玻璃卡组件（M3 3.3）
 *
 * Features:
 * - GlassCard 容器 + spring 折叠动画
 * - 数值格式化（按指标类型）
 * - 变化指示器（up/down arrow）
 * - 骨架屏 100% 覆盖
 * - 错误/空态集成
 */
import { useState } from 'react'
import { GlassCard } from '../ui/GlassCard'
import { INDICATOR_MAP } from '../../constants/indicators'

export interface IndicatorCardProps {
  /** 指标名称 */
  name: string
  /** 当前值 */
  value: number | null
  /** 前值（用于变化指示器）*/
  previousValue?: number | null
  /** 加载中 */
  loading?: boolean
  /** 错误信息 */
  error?: string | null
  /** 是否启用 */
  enabled?: boolean
  /** 点击切换回调 */
  onToggle?: () => void
  /** 自定义显示值（覆盖默认格式化）*/
  customValue?: string
  /** data-testid */
  'data-testid'?: string
}

// ─── 数值格式化 ─────────────────────────────────────────────────────────
function formatValue(name: string, value: number | null): string {
  if (value === null || value === undefined) return '—'

  const def = INDICATOR_MAP[name]
  if (!def) return String(value)

  const { decimalPlaces, isPercent } = def.format
  // 保留指定小数位（不用 toLocaleString，避免精度丢失）
  const fixed = value.toFixed(decimalPlaces)
  // 非百分数且数值较大时加千分位
  const formatted = isPercent || Math.abs(value) < 1000
    ? fixed
    : Number(fixed).toLocaleString('en-US', { minimumFractionDigits: decimalPlaces, maximumFractionDigits: decimalPlaces })
  return isPercent ? `${formatted}%` : formatted
}

// ─── 变化指示器 ─────────────────────────────────────────────────────────
function ChangeIndicator({
  value,
  previousValue,
}: {
  value: number | null
  previousValue?: number | null
}) {
  if (value === null || previousValue === null || previousValue === undefined) return null

  const diff = value - previousValue
  if (Math.abs(diff) < 0.0001) return null

  const isUp = diff > 0
  return (
    <span
      data-testid={`change-indicator-${isUp ? 'up' : 'down'}`}
      aria-label={isUp ? '上升' : '下降'}
      className={[
        'inline-flex items-center text-xs font-medium ml-1',
        isUp ? 'text-kbkkk-accent' : 'text-kbkkk-danger',
      ].join(' ')}
    >
      {/* Arrow SVG */}
      <svg
        viewBox="0 0 12 12"
        className="w-3 h-3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
      >
        {isUp ? (
          <path d="M6 9V3M3 6l3-3 3 3" />
        ) : (
          <path d="M6 3v6M3 6l3 3 3-3" />
        )}
      </svg>
      <span>{Math.abs(diff).toFixed(4)}</span>
    </span>
  )
}

// ─── 骨架屏 ─────────────────────────────────────────────────────────────
function SkeletonContent({ name }: { name: string }) {
  const def = INDICATOR_MAP[name]
  const height = def?.category === 'core' ? 'h-6' : 'h-5'
  return (
    <div data-testid="indicator-card-skeleton" className="animate-pulse space-y-2">
      <div className="h-3 w-16 bg-white/10 rounded" />
      <div className={`${height} w-24 bg-white/10 rounded`} />
      <div className="h-2 w-12 bg-white/5 rounded" />
    </div>
  )
}

// ─── IndicatorCard 主组件 ───────────────────────────────────────────────
export function IndicatorCard({
  name,
  value,
  previousValue,
  loading = false,
  error = null,
  enabled = true,
  onToggle,
  customValue,
  'data-testid': testId,
}: IndicatorCardProps) {
  const [collapsed, setCollapsed] = useState(false)

  const def = INDICATOR_MAP[name]
  const displayName = def?.displayName ?? name
  const isPercent = def?.format.isPercent ?? false

  // 骨架屏（loading 状态）
  if (loading) {
    return (
      <GlassCard
        padding="sm"
        className={`${!enabled ? 'opacity-50' : ''}`}
        data-testid={testId ?? `indicator-card-${name}`}
      >
        <SkeletonContent name={name} />
      </GlassCard>
    )
  }

  // 错误态
  if (error) {
    return (
      <GlassCard
        padding="sm"
        className={`${!enabled ? 'opacity-50' : ''}`}
        data-testid={testId ?? `indicator-card-${name}`}
      >
        <p className="text-xs text-kbkkk-danger">{error}</p>
      </GlassCard>
    )
  }

  const handleClick = () => {
    if (onToggle) onToggle()
    else setCollapsed((c) => !c)
  }

  const formattedValue = customValue ?? formatValue(name, value)

  return (
    <GlassCard
      padding="sm"
      hoverable
      onClick={handleClick}
      className={`${!enabled ? 'opacity-50' : ''} ${collapsed ? 'h-10 overflow-hidden' : ''}`}
      data-testid={testId ?? `indicator-card-${name}`}
    >
      <div className="text-center">
        {/* 指标名称 */}
        <p className="text-xs text-kbkkk-muted mb-1">{displayName}</p>

        {/* 主数值 */}
        <p className="text-lg font-semibold text-kbkkk-text leading-tight">
          {formattedValue}
        </p>

        {/* 变化指示器 */}
        <ChangeIndicator value={value ?? null} previousValue={previousValue ?? null} />

        {/* 分类标签 */}
        {def && (
          <span
            className={[
              'inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded',
              def.category === 'core'
                ? 'bg-kbkkk-accent/20 text-kbkkk-accent'
                : def.category === 'advanced'
                  ? 'bg-purple-500/20 text-purple-400'
                  : 'bg-yellow-500/20 text-yellow-400',
            ].join(' ')}
          >
            {def.category === 'core'
              ? '核心'
              : def.category === 'advanced'
                ? '高级'
                : '预留'}
          </span>
        )}
      </div>
    </GlassCard>
  )
}
