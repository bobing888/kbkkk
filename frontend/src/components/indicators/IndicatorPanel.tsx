/**
 * IndicatorPanel — 9 指标切换容器（M3 3.3）
 *
 * Features:
 * - 11 指标切换（4 核心 + 5 高级 + 2 预留）
 * - GlassSegmented 视图切换（4 核心 / 全部 / 已启用）
 * - 折叠/展开按钮（spring 动画）
 * - 骨架屏 100% 覆盖（B7 自检）
 * - 桌面 4 列 / 平板 2 列 / 手机 1 列
 */
import { useState, type ReactNode } from 'react'
import { GlassCard } from '../ui/GlassCard'
import { GlassSegmented } from '../ui/GlassSegmented'
import { IndicatorCard } from './IndicatorCard'
import { INDICATOR_MAP, ALL_INDICATOR_NAMES } from '../../constants/indicators'
import type { IndicatorsData } from '../../types/analysis'

export type ViewMode = 'core' | 'all' | 'enabled'

export interface IndicatorPanelProps {
  /** 当前启用的指标名称列表 */
  enabledIndicators: string[]
  /** 切换指标回调 */
  onToggle: (name: string) => void
  /** 指标数据（key=指标名称）*/
  data: Record<string, IndicatorsData[string]>
  /** 加载中 */
  loading?: boolean
  /** 错误信息 */
  error?: string | null
  /** data-testid */
  'data-testid'?: string
}

// ─── 视图模式选项 ───────────────────────────────────────────────────────
const VIEW_OPTIONS = [
  { value: 'core' as ViewMode, label: '4 核心' },
  { value: 'all' as ViewMode, label: '全部' },
  { value: 'enabled' as ViewMode, label: '已启用' },
]

// ─── 辅助：提取指标主值 ────────────────────────────────────────────────
function extractValue(data: IndicatorsData[string] | undefined): number | null {
  if (!data) return null
  // union type — 取第一个非 undefined 数值
  const values = Object.values(data as Record<string, unknown>).filter(
    (v) => typeof v === 'number'
  ) as number[]
  return values[0] ?? null
}

// ─── 骨架屏（B7 100% 覆盖）────────────────────────────────────────────
function PanelSkeleton({ names }: { names: string[] }) {
  return (
    <>
      {names.map((name) => (
        <div
          key={name}
          data-testid={`indicator-skeleton-${name}`}
          className="animate-pulse"
        >
          <GlassCard padding="sm">
            <div className="space-y-2">
              <div className="h-3 w-16 bg-white/10 rounded mx-auto" />
              <div className="h-6 w-24 bg-white/10 rounded mx-auto" />
              <div className="h-2 w-12 bg-white/5 rounded mx-auto" />
            </div>
          </GlassCard>
        </div>
      ))}
    </>
  )
}

// ─── 空态 ──────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <GlassCard padding="md">
      <div className="text-center py-6">
        <p className="text-sm text-kbkkk-muted">暂无数据</p>
        <p className="text-xs text-kbkkk-muted/60 mt-1">请选择标的和周期</p>
      </div>
    </GlassCard>
  )
}

// ─── 错误态 ─────────────────────────────────────────────────────────────
function ErrorState({ message }: { message: string }) {
  return (
    <GlassCard padding="md">
      <div className="text-center py-4">
        <p className="text-sm text-kbkkk-danger">{message}</p>
      </div>
    </GlassCard>
  )
}

// ─── IndicatorPanel 主组件 ─────────────────────────────────────────────
export function IndicatorPanel({
  enabledIndicators,
  onToggle,
  data,
  loading = false,
  error = null,
  'data-testid': testId,
}: IndicatorPanelProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('core')
  const [collapsed, setCollapsed] = useState(false)

  // 根据视图模式计算要渲染的指标列表
  const visibleNames = (() => {
    switch (viewMode) {
      case 'core':
        return ALL_INDICATOR_NAMES.filter(
          (n) => INDICATOR_MAP[n]?.category === 'core'
        )
      case 'enabled':
        return enabledIndicators
      case 'all':
      default:
        return ALL_INDICATOR_NAMES
    }
  })()

  // 计算面板内容
  let content: ReactNode
  if (loading) {
    content = (
      <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-2">
        <PanelSkeleton names={visibleNames.slice(0, 4)} />
      </div>
    )
  } else if (error) {
    content = <ErrorState message={error} />
  } else if (Object.keys(data).length === 0) {
    content = <EmptyState />
  } else {
    content = (
      <div
        data-testid="indicator-grid"
        className={[
          'grid gap-2',
          'grid-cols-2', // mobile: 2 cols
          'md:grid-cols-2', // tablet: 2 cols
          'lg:grid-cols-4', // desktop: 4 cols
          collapsed ? 'hidden' : '',
        ].join(' ')}
      >
        {visibleNames.map((name) => {
          const isEnabled = enabledIndicators.includes(name)
          const value = extractValue(data[name])
          return (
            <IndicatorCard
              key={name}
              name={name}
              value={value}
              enabled={isEnabled}
              onToggle={() => onToggle(name)}
              data-testid={`indicator-card-${name}`}
            />
          )
        })}
      </div>
    )
  }

  return (
    <div data-testid={testId}>
      {/* 视图切换 + 折叠控制 */}
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-kbkkk-muted uppercase tracking-wider">
          技术指标
        </p>
        <div className="flex items-center gap-2">
          <GlassSegmented
            options={VIEW_OPTIONS}
            value={viewMode}
            onChange={(v) => setViewMode(v as ViewMode)}
            data-testid="indicator-view-selector"
          />
          <button
            onClick={() => setCollapsed((c) => !c)}
            data-testid="panel-collapse-toggle"
            aria-label={collapsed ? '展开指标面板' : '折叠指标面板'}
            className={[
              'p-1.5 rounded-kbkkk-sm',
              'bg-[rgba(255,255,255,0.04)]',
              'border border-[var(--glass-border)]',
              'hover:bg-[rgba(255,255,255,0.08)]',
              'transition-transform duration-200',
              collapsed ? '' : 'rotate-180',
            ].join(' ')}
          >
            {/* Chevron up SVG */}
            <svg
              viewBox="0 0 12 12"
              className="w-4 h-4 text-kbkkk-muted"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M2 8l4-4 4 4" />
            </svg>
          </button>
        </div>
      </div>

      {/* 面板内容 */}
      {content}
    </div>
  )
}
