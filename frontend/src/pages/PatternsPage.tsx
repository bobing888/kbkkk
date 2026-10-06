/**
 * PatternsPage — 形态识别可视化页（M3 3.5）
 * V2 §3.5 强制：11 形态（3 反转 + 3 持续 + 3 中继 + 2 警告）+ 双视图 + 详情弹层
 * 双视图：K线标注视图（markers 已接通）+ 列表视图
 * License: Original work for kbkkk project.
 */
import { useState, useCallback } from 'react'
import { GlassCard } from '../components/ui/GlassCard'
import { GlassSegmented } from '../components/ui/GlassSegmented'
import { KLineChart } from '../components/KLineChart'
import { PatternList } from '../components/patterns/PatternList'
import { PatternDetailModal } from '../components/patterns/PatternDetailModal'
import { ChartSkeleton } from '../components/common/ChartSkeleton'
import { ErrorMessage } from '../components/common/ErrorMessage'
import { EmptyState } from '../components/common/EmptyState'
import { PATTERN_MAP, PATTERN_FILTER_OPTIONS, type PatternCategory } from '../constants/patterns'
import type { PatternItem } from '../types/analysis'
import type { KLineData } from '../types/kline'
import type { SegmentedOption } from '../components/ui/GlassSegmented'

type PatternFilter = PatternCategory | 'all'
type ViewMode = 'chart' | 'list'

interface PatternsPageProps {
  /** K 线数据 */
  klineData?: KLineData[]
  /** 形态数据 */
  patterns?: PatternItem[]
  /** 是否加载中 */
  loading?: boolean
  /** 错误信息 */
  error?: string | null
  /** 标的符号 */
  symbol?: string
}

/** 视图切换选项 */
const VIEW_OPTIONS: SegmentedOption<'chart' | 'list'>[] = [
  { value: 'chart', label: 'K线标注' },
  { value: 'list', label: '列表' },
]

export function PatternsPage({
  klineData = [],
  patterns = [],
  loading = false,
  error = null,
  symbol = 'BTC',
}: PatternsPageProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('chart')
  const [activeFilter, setActiveFilter] = useState<PatternFilter>('all')
  const [selectedPattern, setSelectedPattern] = useState<PatternItem | null>(null)

  // 过滤形态
  const filteredPatterns = activeFilter === 'all'
    ? patterns
    : patterns.filter((p) => {
        const def = PATTERN_MAP[p.name]
        return def?.category === activeFilter
      })

  // 选中形态的 def
  const selectedDef = selectedPattern ? PATTERN_MAP[selectedPattern.name] : null

  const handleCardClick = useCallback((pattern: PatternItem) => {
    setSelectedPattern(pattern)
  }, [])

  const handleCloseModal = useCallback(() => {
    setSelectedPattern(null)
  }, [])

  return (
    <div data-testid="patterns-page" className="space-y-4 pb-8">
      {/* 页面标题 */}
      <div className="pt-2 pb-1">
        <h1 className="text-xl font-semibold text-kbkkk-text">形态识别</h1>
        <p className="text-sm text-kbkkk-muted mt-0.5">
          K 线形态 · BTC/ETH · 11 种形态
        </p>
      </div>

      {/* 顶部控制栏 */}
      <div className="flex flex-col gap-3">
        {/* 视图切换 + 统计 */}
        <div className="flex items-center justify-between gap-3">
          <GlassSegmented
            options={VIEW_OPTIONS}
            value={viewMode}
            onChange={(val) => setViewMode(Array.isArray(val) ? val[0] : val)}
            data-testid="patterns-view-switcher"
          />
          <div className="text-xs text-kbkkk-muted tabular-nums">
            {filteredPatterns.length} 个形态
          </div>
        </div>

        {/* 过滤栏 */}
        <div className="flex flex-wrap gap-2">
          {PATTERN_FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              data-testid={`filter-${opt.value}`}
              onClick={() => setActiveFilter(opt.value as PatternFilter)}
              className={`px-3 py-1.5 text-xs rounded-full transition-all ${
                activeFilter === opt.value
                  ? 'bg-kbkkk-accent/20 text-kbkkk-accent border border-kbkkk-accent/30'
                  : 'bg-kbkkk-surface text-kbkkk-muted border border-transparent hover:bg-kbkkk-surface/80'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* 双视图内容 */}
      {viewMode === 'chart' ? (
        /* ── K线标注视图 ── */
        <div data-testid="patterns-chart-container" className="space-y-3">
          {/* 图表 */}
          <GlassCard padding="none" className="h-80 overflow-hidden">
            {loading ? (
              <ChartSkeleton />
            ) : error ? (
              <ErrorMessage message={error} />
            ) : klineData.length === 0 ? (
              <EmptyState message="暂无 K 线数据" />
            ) : (
              <KLineChart
                symbol={symbol}
                data={klineData}
                patterns={filteredPatterns}
                signals={[]}
              />
            )}
          </GlassCard>

          {/* 形态图例 */}
          {filteredPatterns.length > 0 && (
            <GlassCard padding="sm">
              <div className="flex flex-wrap gap-3">
                {(['reversal', 'continuation', 'midline', 'warning'] as PatternCategory[]).map(
                  (cat) => {
                    const count = filteredPatterns.filter(
                      (p) => PATTERN_MAP[p.name]?.category === cat
                    ).length
                    if (count === 0) return null
                    const color =
                      cat === 'reversal' || cat === 'warning'
                        ? '#f7931a'
                        : '#16c784'
                    return (
                      <div key={cat} className="flex items-center gap-1.5">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: color }}
                        />
                        <span className="text-xs text-kbkkk-muted">
                          {PATTERN_FILTER_OPTIONS.find((o) => o.value === cat)?.label ?? cat}
                        </span>
                        <span className="text-xs font-semibold text-kbkkk-text">{count}</span>
                      </div>
                    )
                  }
                )}
              </div>
            </GlassCard>
          )}
        </div>
      ) : (
        /* ── 列表视图 ── */
        <div data-testid="patterns-list-container">
          <PatternList
            patterns={filteredPatterns}
            loading={loading}
            error={error ?? undefined}
            onCardClick={handleCardClick}
          />
        </div>
      )}

      {/* 详情弹层 */}
      {selectedPattern && selectedDef && (
        <PatternDetailModal
          pattern={selectedPattern}
          def={selectedDef}
          isOpen={true}
          onClose={handleCloseModal}
        />
      )}
    </div>
  )
}
