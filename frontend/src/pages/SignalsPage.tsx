/**
 * SignalsPage — 信号中心（M3 3.4 完成版）
 * V2 §3.4 强制：WebSocket 实时信号流 + 连接状态指示器 + 5 类过滤
 * License: Original work for kbkkk project.
 */
import { useState } from 'react'
import { GlassCard } from '../components/ui/GlassCard'
import { SignalList } from '../components/signals/SignalList'
import { useWebSocketSignals } from '../hooks/useWebSocketSignals'
import type { SignalFilter } from '../components/signals/SignalList'
import type { ConnectionStatus } from '../lib/websocket'

// ─── 连接状态颜色映射 ────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<ConnectionStatus, { label: string; color: string; bg: string }> = {
  CONNECTING: { label: '连接中…', color: '#f7931a', bg: 'rgba(247,147,26,0.12)' },
  OPEN: { label: '已连接', color: '#16c784', bg: 'rgba(22,199,132,0.12)' },
  RECONNECTING: { label: '重连中…', color: '#f7931a', bg: 'rgba(247,147,26,0.12)' },
  CLOSING: { label: '断开中…', color: '#6b7280', bg: 'rgba(107,114,128,0.12)' },
  CLOSED: { label: '未连接', color: '#ea3943', bg: 'rgba(234,57,67,0.12)' },
}

/** 连接状态指示器 */
function ConnectionStatusBadge({ status }: { status: ConnectionStatus }) {
  const cfg = STATUS_CONFIG[status]
  return (
    <div
      data-testid="connection-status"
      className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium transition-all"
      style={{ color: cfg.color, backgroundColor: cfg.bg, border: `1px solid ${cfg.color}33` }}
    >
      <span
        aria-hidden="true"
        className="w-1.5 h-1.5 rounded-full animate-pulse"
        style={{ backgroundColor: cfg.color }}
      />
      {cfg.label}
    </div>
  )
}

/** 过滤按钮 */
function FilterButton({
  filter,
  active,
  onClick,
}: {
  filter: SignalFilter
  active: boolean
  onClick: () => void
}) {
  const labels: Record<SignalFilter, string> = {
    all: '全部',
    long: '做多',
    short: '做空',
    neutral: '中性',
  }
  return (
    <button
      data-testid={`filter-${filter}`}
      onClick={onClick}
      className={`px-3 py-1.5 text-xs rounded-full transition-all ${
        active
          ? 'bg-kbkkk-accent/20 text-kbkkk-accent border border-kbkkk-accent/30'
          : 'bg-kbkkk-surface text-kbkkk-muted border border-transparent hover:bg-kbkkk-surface/80'
      }`}
    >
      {labels[filter]}
    </button>
  )
}

// ─── Filters ────────────────────────────────────────────────────────────────

const FILTERS: SignalFilter[] = ['all', 'long', 'short', 'neutral']

export function SignalsPage() {
  const { status, signals } = useWebSocketSignals()
  const [activeFilter, setActiveFilter] = useState<SignalFilter>('all')

  return (
    <div data-testid="signals-page" className="space-y-4 pb-8">
      {/* 页面标题 */}
      <div className="pt-2 pb-1 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-kbkkk-text">信号中心</h1>
          <p className="text-sm text-kbkkk-muted mt-0.5">
            实时共振信号 · BTC/ETH
          </p>
        </div>
        <ConnectionStatusBadge status={status} />
      </div>

      {/* 信号统计 */}
      <GlassCard padding="sm">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-kbkkk-muted uppercase tracking-wider">当前信号</p>
            <p className="text-2xl font-bold text-kbkkk-text mt-0.5 tabular-nums">
              {signals.length}
            </p>
          </div>
          <div className="flex gap-3 text-right">
            {(['long', 'short', 'neutral'] as const).map((dir) => {
              const count = signals.filter((s) => s.direction === dir).length
              return (
                <div key={dir}>
                  <p className="text-xs text-kbkkk-muted uppercase tracking-wider">
                    {dir === 'long' ? '做多' : dir === 'short' ? '做空' : '中性'}
                  </p>
                  <p
                    className="text-lg font-bold tabular-nums mt-0.5"
                    style={{
                      color:
                        dir === 'long' ? '#f7931a' : dir === 'short' ? '#ea3943' : '#16c784',
                    }}
                  >
                    {count}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      </GlassCard>

      {/* 信号列表 */}
      <SignalList
        signals={signals}
        filter={activeFilter}
        data-testid="signals-list"
      />

      {/* 过滤控制 */}
      <div className="flex gap-2">
        {FILTERS.map((f) => (
          <FilterButton
            key={f}
            filter={f}
            active={activeFilter === f}
            onClick={() => setActiveFilter(f)}
          />
        ))}
      </div>
    </div>
  )
}
