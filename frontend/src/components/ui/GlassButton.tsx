/**
 * GlassButton — macOS Sonoma glass button
 *
 * Features:
 * - backdrop-blur: 12px (lighter blur than card)
 * - Three variants: default, primary (accent), ghost
 * - Three sizes: sm, md, lg
 * - Keyboard accessible
 */
import { type ReactNode, type ButtonHTMLAttributes } from 'react'

export interface GlassButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'type'> {
  /** Button label or content */
  children: ReactNode
  /** Visual variant */
  variant?: 'default' | 'primary' | 'ghost'
  /** Button size */
  size?: 'sm' | 'md' | 'lg'
  /** Show loading spinner */
  loading?: boolean
  /** data-testid for testing */
  'data-testid'?: string
}

const SIZE_CLASSES = {
  sm: 'px-3 py-1.5 text-kbkkk-sm gap-1.5',
  md: 'px-4 py-2 text-kbkkk-base gap-2',
  lg: 'px-6 py-3 text-kbkkk-lg gap-2',
} as const

const VARIANT_CLASSES = {
  default: [
    'bg-[var(--glass-bg)]',
    'border border-[var(--glass-border)]',
    'text-kbkkk-text',
    'hover:bg-white/[0.12] hover:border-white/[0.2]',
    'active:bg-white/[0.04]',
  ].join(' '),
  primary: [
    'bg-kbkkk-accent/90',
    'border border-kbkkk-accent',
    'text-kbkkk-bg font-semibold',
    'hover:bg-kbkkk-accent hover:border-kbkkk-accent',
    'active:opacity-80',
  ].join(' '),
  ghost: [
    'bg-transparent',
    'border border-transparent',
    'text-kbkkk-text-secondary',
    'hover:bg-white/[0.06] hover:border-[var(--glass-border)] hover:text-kbkkk-text',
    'active:bg-white/[0.04]',
  ].join(' '),
} as const

/**
 * GlassButton — macOS Sonoma style glass button.
 */
export function GlassButton({
  children,
  variant = 'default',
  size = 'md',
  loading = false,
  disabled,
  className = '',
  'data-testid': testId,
  ...rest
}: GlassButtonProps) {
  const isDisabled = disabled || loading

  return (
    <button
      data-testid={testId}
      disabled={isDisabled}
      className={[
        'relative inline-flex items-center justify-center',
        'rounded-kbkkk-md',
        'backdrop-blur-glass-light',
        'font-medium',
        'transition-all duration-150',
        'select-none',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-kbkkk-accent focus-visible:ring-offset-2 focus-visible:ring-offset-kbkkk-bg',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        isDisabled ? 'opacity-40 cursor-not-allowed pointer-events-none' : 'cursor-pointer',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...rest}
    >
      {loading && (
        <span
          aria-hidden="true"
          className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"
        />
      )}
      {children}
    </button>
  )
}
