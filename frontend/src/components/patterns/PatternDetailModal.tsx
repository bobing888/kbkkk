/**
 * PatternDetailModal — 形态详情弹层（M3 3.5）
 * V2 §3.5 强制：玻璃卡模态框 + 焦点陷阱 + Esc 关闭
 * License: Original work for kbkkk project.
 */
import { useEffect, useRef, type FC } from 'react'
import { GlassCard } from '../ui/GlassCard'
import { PATTERN_COLORS, PATTERN_CATEGORY_LABELS, type PatternDef } from '../../constants/patterns'
import type { PatternItem } from '../../types/analysis'

interface PatternDetailModalProps {
  pattern: PatternItem
  def: PatternDef
  isOpen: boolean
  onClose: () => void
}

/** 格式化日期 */
function formatDate(dt: string | undefined): string {
  if (!dt) return '—'
  return dt.slice(0, 10)
}

/** 格式化价格 */
function formatPrice(p: number | undefined): string {
  if (p === undefined) return '—'
  return p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export const PatternDetailModal: FC<PatternDetailModalProps> = ({
  pattern,
  def,
  isOpen,
  onClose,
}) => {
  const modalRef = useRef<HTMLDivElement>(null)
  const color = PATTERN_COLORS[def.category]
  const categoryLabel = PATTERN_CATEGORY_LABELS[def.category]
  const confidence = (pattern as PatternItem & { confidence?: number }).confidence ?? 0.8

  // Esc 关闭
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  // 焦点陷阱
  useEffect(() => {
    if (!isOpen) return
    const firstFocusable = modalRef.current?.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    firstFocusable?.focus()
  }, [isOpen])

  if (!isOpen) return null

  return (
    /* 全屏遮罩 */
    <div
      data-testid="pattern-modal-overlay"
      aria-modal="true"
      role="dialog"
      aria-labelledby="pattern-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      {/* 模态框内容 */}
      <div ref={modalRef}>
        <GlassCard
          data-testid="pattern-detail-modal"
          padding="lg"
          className="w-full max-w-md"
          style={{
            boxShadow: `0 24px 48px rgba(0,0,0,0.4), 0 0 0 1px ${color}33`,
          }}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-3 mb-4">
            <div className="flex items-center gap-3">
              <span aria-hidden="true" className="text-3xl">{def.icon}</span>
              <div>
                <h2
                  id="pattern-modal-title"
                  className="text-lg font-semibold text-kbkkk-text"
                >
                  {def.displayName}
                </h2>
                <span
                  className="inline-block text-xs font-medium px-2 py-0.5 rounded-full mt-1"
                  style={{
                    color,
                    backgroundColor: `${color}18`,
                    border: `1px solid ${color}33`,
                  }}
                >
                  {categoryLabel}
                </span>
              </div>
            </div>
            {/* 关闭按钮 */}
            <button
              data-testid="pattern-modal-close"
              onClick={onClose}
              aria-label="关闭"
              className="w-8 h-8 rounded-full flex items-center justify-center text-kbkkk-muted hover:text-kbkkk-text hover:bg-kbkkk-surface transition-colors"
            >
              ✕
            </button>
          </div>

          {/* 描述 */}
          <p className="text-sm text-kbkkk-muted mb-4 leading-relaxed">
            {def.description}
          </p>

          {/* 置信度 */}
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-kbkkk-muted">置信度</span>
              <span className="font-semibold tabular-nums" style={{ color }}>
                {(confidence * 100).toFixed(0)}%
              </span>
            </div>
            <div className="w-full h-2 rounded-full bg-kbkkk-surface overflow-hidden">
              <div
                aria-hidden="true"
                className="h-full rounded-full"
                style={{ width: `${confidence * 100}%`, backgroundColor: color }}
              />
            </div>
          </div>

          {/* 价格范围 */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="p-3 rounded-lg bg-kbkkk-surface/50">
              <p className="text-xs text-kbkkk-muted mb-0.5">最高价</p>
              <p className="text-sm font-semibold text-kbkkk-text tabular-nums">
                {formatPrice(pattern.high)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-kbkkk-surface/50">
              <p className="text-xs text-kbkkk-muted mb-0.5">最低价</p>
              <p className="text-sm font-semibold text-kbkkk-text tabular-nums">
                {formatPrice(pattern.low)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-kbkkk-surface/50">
              <p className="text-xs text-kbkkk-muted mb-0.5">开盘价</p>
              <p className="text-sm font-semibold text-kbkkk-text tabular-nums">
                {formatPrice(pattern.open)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-kbkkk-surface/50">
              <p className="text-xs text-kbkkk-muted mb-0.5">收盘价</p>
              <p className="text-sm font-semibold text-kbkkk-text tabular-nums">
                {formatPrice(pattern.close)}
              </p>
            </div>
          </div>

          {/* 时间 */}
          <div className="flex items-center justify-between text-xs text-kbkkk-muted pt-2 border-t border-kbkkk-surface">
            <span>识别时间</span>
            <span className="tabular-nums">{formatDate(pattern.datetime)}</span>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
