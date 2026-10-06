/**
 * GlassCard — macOS Sonoma glass surface container
 *
 * Features:
 * - backdrop-blur: 20px (glass effect)
 * - Semi-transparent background
 * - Subtle top-edge highlight
 * - Configurable padding and shadow
 */
import { type ReactNode } from 'react'

export interface GlassCardProps {
  /** Card content */
  children: ReactNode
  /** Additional CSS class */
  className?: string
  /** Padding size */
  padding?: 'none' | 'sm' | 'md' | 'lg'
  /** Show hover shadow transition */
  hoverable?: boolean
  /** data-testid for testing */
  'data-testid'?: string
}

const PADDING_MAP = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
} as const

/**
 * GlassCard — macOS Sonoma style glass container.
 * Uses CSS variables from globals.css + Tailwind utility classes.
 */
export function GlassCard({
  children,
  className = '',
  padding = 'md',
  hoverable = false,
  'data-testid': testId,
}: GlassCardProps) {
  return (
    <div
      data-testid={testId}
      className={[
        'relative rounded-kbkkk-lg overflow-hidden',
        'bg-[var(--glass-bg)]',
        'border border-[var(--glass-border)]',
        'shadow-glass',
        'backdrop-blur-glass',
        hoverable ? 'transition-shadow duration-200 hover:shadow-glass-hover cursor-pointer' : '',
        PADDING_MAP[padding],
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {/* Top-edge highlight (macOS light reflection) */}
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 h-px bg-white/[0.06] rounded-t-kbkkk-lg"
      />
      {children}
    </div>
  )
}
