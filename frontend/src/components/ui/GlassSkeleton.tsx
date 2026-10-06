/**
 * GlassSkeleton — macOS Sonoma skeleton loading state
 *
 * Features:
 * - Glass background shimmer animation
 * - Configurable height, width, border-radius
 * - Multiple variants (text, circle, rect)
 * - Accessible (role="status", aria-label)
 */
import type { ReactNode } from 'react'

export interface GlassSkeletonProps {
  /** Skeleton variant */
  variant?: 'text' | 'circle' | 'rect' | 'chart'
  /** Custom width */
  width?: string
  /** Custom height */
  height?: string
  /** CSS class for container */
  className?: string
  /** Show label text below skeleton */
  label?: string
  /** data-testid for testing */
  'data-testid'?: string
}

const VARIANT_STYLES = {
  text: { height: '16px', borderRadius: 'var(--radius-sm)' },
  circle: { width: '40px', height: '40px', borderRadius: '50%' },
  rect: { height: '80px', borderRadius: 'var(--radius-md)' },
  chart: { height: '64px', borderRadius: 'var(--radius-sm)' },
} as const

/**
 * GlassSkeleton — loading placeholder with glass shimmer.
 */
export function GlassSkeleton({
  variant = 'rect',
  width,
  height,
  className = '',
  label,
  'data-testid': testId,
}: GlassSkeletonProps) {
  const variantStyle = VARIANT_STYLES[variant]

  return (
    <div
      data-testid={testId}
      role="status"
      aria-label={label ?? '加载中'}
      className={['flex flex-col items-center gap-3', className].filter(Boolean).join(' ')}
    >
      <div
        className={[
          'w-full glass-shimmer',
          variant === 'chart' ? 'flex items-end gap-1' : '',
        ].join(' ')}
        style={{
          width: width ?? variantStyle.width,
          height: height ?? variantStyle.height,
          borderRadius: variant === 'circle' ? '50%' : variantStyle.borderRadius,
        }}
      >
        {variant === 'chart' && <ChartBars />}
      </div>
      {label && (
        <span className="text-kbkkk-muted text-kbkkk-xs animate-pulse">{label}</span>
      )}

      <style>{`
        .glass-shimmer {
          background: linear-gradient(
            90deg,
            rgba(255,255,255,0.04) 0%,
            rgba(255,255,255,0.10) 50%,
            rgba(255,255,255,0.04) 100%
          );
          background-size: 200% 100%;
          animation: skeleton-shimmer 1.6s ease-in-out infinite;
        }
        @keyframes skeleton-shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  )
}

/** Chart bar skeleton — mimics KLineChart skeleton pattern */
function ChartBars() {
  const heights = [45, 60, 55, 70, 65, 80, 75, 60, 85, 70, 90, 75, 80, 65, 95, 80, 70, 60, 75, 55]
  return (
    <>
      {heights.map((h, i) => (
        <div
          key={i}
          className="flex-1 glass-shimmer rounded-sm"
          style={{ height: `${h}%`, animationDelay: `${i * 50}ms` }}
        />
      ))}
    </>
  )
}
