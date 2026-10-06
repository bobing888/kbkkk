/**
 * GlassSegmented — macOS Sonoma segmented control
 *
 * Features:
 * - Glass pill container
 * - Multiple segments with selection state
 * - Single or multi-select mode
 * - Spring-like indicator slide (CSS only)
 * - Keyboard navigation
 */
import { useState } from 'react'

export interface SegmentedOption<T extends string> {
  value: T
  label: string
  icon?: React.ReactNode
  disabled?: boolean
}

export interface GlassSegmentedProps<T extends string> {
  /** Available options */
  options: SegmentedOption<T>[]
  /** Selected value(s) */
  value: T | T[]
  /** On change handler */
  onChange: (value: T | T[]) => void
  /** Allow multi-select */
  multi?: boolean
  /** CSS class */
  className?: string
  /** data-testid for testing */
  'data-testid'?: string
}

/**
 * GlassSegmented — macOS Sonoma style segmented control.
 */
export function GlassSegmented<T extends string>({
  options,
  value,
  onChange,
  multi = false,
  className = '',
  'data-testid': testId,
}: GlassSegmentedProps<T>) {
  const selectedValues = Array.isArray(value) ? value : [value]
  const [focusedIndex, setFocusedIndex] = useState<number | null>(null)

  const handleSelect = (opt: SegmentedOption<T>) => {
    if (opt.disabled) return
    if (multi) {
      const next = selectedValues.includes(opt.value)
        ? selectedValues.filter((v) => v !== opt.value)
        : [...selectedValues, opt.value]
      onChange(next)
    } else {
      onChange(opt.value)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      const next = (index + 1) % options.length
      const nextOpt = options[next]
      if (!nextOpt.disabled) {
        if (!multi) onChange(nextOpt.value)
        setFocusedIndex(next)
        document.querySelector<HTMLElement>(`[data-seg-index="${next}"]`)?.focus()
      }
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      const prev = (index - 1 + options.length) % options.length
      const prevOpt = options[prev]
      if (!prevOpt.disabled) {
        if (!multi) onChange(prevOpt.value)
        setFocusedIndex(prev)
        document.querySelector<HTMLElement>(`[data-seg-index="${prev}"]`)?.focus()
      }
    }
  }

  return (
    <div
      data-testid={testId}
      role={multi ? 'group' : 'radiogroup'}
      aria-label="segmented control"
      className={[
        'inline-flex items-center',
        'rounded-kbkkk-md',
        'p-1',
        'bg-[rgba(255,255,255,0.04)]',
        'border border-[var(--glass-border)]',
        'backdrop-blur-glass-light',
        'gap-1',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {options.map((opt, index) => {
        const isSelected = selectedValues.includes(opt.value)
        return (
          <button
            key={opt.value}
            data-testid={testId ? `${testId}-option-${opt.value}` : undefined}
            data-seg-index={index}
            role={multi ? 'checkbox' : 'radio'}
            aria-checked={isSelected}
            aria-disabled={opt.disabled}
            disabled={opt.disabled}
            onClick={() => handleSelect(opt)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            onFocus={() => setFocusedIndex(index)}
            className={[
              'relative z-10',
              'flex items-center gap-1.5',
              'px-3 py-1.5',
              'rounded-kbkkk-sm',
              'text-kbkkk-sm font-medium',
              'transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-kbkkk-accent focus-visible:ring-offset-1 focus-visible:ring-offset-kbkkk-bg',
              'select-none',
              isSelected
                ? 'text-kbkkk-text bg-[rgba(255,255,255,0.12)] shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]'
                : 'text-kbkkk-muted hover:text-kbkkk-text-secondary hover:bg-[rgba(255,255,255,0.04)]',
              opt.disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            {opt.icon && <span aria-hidden="true">{opt.icon}</span>}
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
