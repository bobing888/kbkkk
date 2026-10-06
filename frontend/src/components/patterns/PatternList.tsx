/**
 * PatternList — 形态列表（M3 3.5）
 * V2 §3.5 强制：3/2/1 列响应式 + 骨架屏 + 空态 + 错误态
 * License: Original work for kbkkk project.
 */
import type { FC } from 'react'
import { PatternCard } from './PatternCard'
import { GlassCard } from '../ui/GlassCard'
import { EmptyState } from '../common/EmptyState'
import { ErrorMessage } from '../common/ErrorMessage'
import { PATTERN_MAP } from '../../constants/patterns'
import type { PatternItem } from '../../types/analysis'

interface PatternListProps {
  patterns: PatternItem[]
  loading?: boolean
  error?: string | null
  onCardClick: (pattern: PatternItem) => void
  /** 测试 id */
  'data-testid'?: string
}

/** 骨架屏 */
function PatternListSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <GlassCard
          key={i}
          data-testid={`pattern-skeleton-${i}`}
          padding="sm"
          className="animate-pulse"
        >
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-gray-600" />
              <div className="w-20 h-4 rounded bg-gray-600" />
            </div>
            <div className="w-full h-1.5 rounded-full bg-gray-600" />
            <div className="w-16 h-3 rounded bg-gray-600 self-end" />
          </div>
        </GlassCard>
      ))}
    </div>
  )
}

export const PatternList: FC<PatternListProps> = ({
  patterns,
  loading = false,
  error = null,
  onCardClick,
  'data-testid': testId,
}) => {
  if (loading) {
    return (
      <div data-testid={testId ?? 'pattern-list'}>
        <PatternListSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div data-testid={testId ?? 'pattern-list'}>
        <GlassCard data-testid="pattern-list-error" padding="lg">
          <ErrorMessage message={error} />
        </GlassCard>
      </div>
    )
  }

  if (patterns.length === 0) {
    return (
      <div data-testid={testId ?? 'pattern-list'}>
        <GlassCard data-testid="empty-state" padding="lg">
          <EmptyState message="暂未识别到形态" />
        </GlassCard>
      </div>
    )
  }

  return (
    <div
      data-testid={testId ?? 'pattern-list'}
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
    >
      {patterns.map((pattern, i) => {
        const def = PATTERN_MAP[pattern.name]
        if (!def) return null
        return (
          <PatternCard
            key={`${pattern.datetime ?? ''}-${pattern.name}-${i}`}
            pattern={pattern}
            def={def}
            onClick={() => onCardClick(pattern)}
            data-testid={`pattern-card-${i}`}
          />
        )
      })}
    </div>
  )
}
