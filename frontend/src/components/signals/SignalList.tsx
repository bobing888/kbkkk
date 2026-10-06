/**
 * SignalList — 信号列表 + 过滤（M3 3.4）
 * V2 §3.4 强制：5 类过滤 + 虚拟列表（max 50 visible）+ 加载/错误/空态
 * License: Original work for kbkkk project.
 */
import type { FC } from 'react'
import { SignalCard } from './SignalCard'
import { GlassCard } from '../ui/GlassCard'
import type { SignalItem } from '../../types/analysis'
import type { SignalDirection } from '../../types/analysis'

export type SignalFilter = SignalDirection | 'all'

interface SignalListProps {
  signals: SignalItem[]
  filter: SignalFilter
  loading?: boolean
  error?: string | null
  onSignalClick?: (signal: SignalItem) => void
  /** 测试 id */
  'data-testid'?: string
}

const FILTER_LABELS: Record<SignalFilter, string> = {
  all: '全部',
  long: '做多',
  short: '做空',
  neutral: '中性',
}

const MAX_VISIBLE = 50

/** 过滤信号 */
function filterSignals(signals: SignalItem[], filter: SignalFilter): SignalItem[] {
  if (filter === 'all') return signals
  return signals.filter((s) => s.direction === filter)
}

export const SignalList: FC<SignalListProps> = ({
  signals,
  filter,
  loading = false,
  error = null,
  onSignalClick,
  'data-testid': testId,
}) => {
  const filtered = filterSignals(signals, filter).slice(0, MAX_VISIBLE)

  if (loading) {
    return (
      <GlassCard data-testid="signal-list-loading" padding="lg" className="flex items-center justify-center min-h-48">
        <div className="flex flex-col items-center gap-3 text-kbkkk-muted">
          <div className="w-8 h-8 border-2 border-kbkkk-accent border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">加载信号中…</p>
        </div>
      </GlassCard>
    )
  }

  if (error) {
    return (
      <GlassCard data-testid="signal-list-error" padding="lg" className="flex items-center justify-center min-h-48">
        <div className="text-center text-kbkkk-danger">
          <p className="text-2xl mb-2">⚠️</p>
          <p className="text-sm">{error}</p>
        </div>
      </GlassCard>
    )
  }

  if (filtered.length === 0) {
    return (
      <GlassCard data-testid="signal-list-empty" padding="lg" className="flex items-center justify-center min-h-48">
        <div className="text-center text-kbkkk-muted">
          <p className="text-4xl mb-2">🔔</p>
          <p className="text-sm">
            {filter === 'all' ? '暂无信号' : `暂无${FILTER_LABELS[filter]}信号`}
          </p>
          <p className="text-xs mt-1 opacity-60">ADX ≥ 25 时触发</p>
        </div>
      </GlassCard>
    )
  }

  return (
    <div data-testid={testId ?? 'signal-list'} className="flex flex-col gap-2 max-h-[60vh] overflow-y-auto">
      {filtered.map((signal, i) => (
        <SignalCard
          key={`${signal.datetime ?? ''}-${signal.name}-${i}`}
          signal={signal}
          onClick={onSignalClick ? () => onSignalClick(signal) : undefined}
          data-testid={`signal-card-${i}`}
        />
      ))}
      {signals.length > MAX_VISIBLE && (
        <p className="text-xs text-kbkkk-muted text-center py-2">
          显示 {MAX_VISIBLE} / {signals.length} 条
        </p>
      )}
    </div>
  )
}
