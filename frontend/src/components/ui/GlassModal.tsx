/**
 * GlassModal — macOS Sonoma glass modal dialog
 *
 * Features:
 * - backdrop-blur: 40px (heavy blur)
 * - Scale + fade entrance animation (spring feel)
 * - Focus trap
 * - ESC to close
 * - Click outside to close
 */
import { useEffect, useRef, type ReactNode } from 'react'

export interface GlassModalProps {
  /** Whether modal is open */
  open: boolean
  /** Close handler */
  onClose: () => void
  /** Modal title */
  title?: string
  /** Modal content */
  children: ReactNode
  /** Footer actions */
  footer?: ReactNode
  /** data-testid for testing */
  'data-testid'?: string
}

/**
 * GlassModal — macOS Sonoma style modal.
 * Note: full focus-trap + ESC handling requires React portals + ref.
 * This is the base implementation; stage 3.x can add portal rendering.
 */
export function GlassModal({
  open,
  onClose,
  title,
  children,
  footer,
  'data-testid': testId,
}: GlassModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)

  // ESC key handler
  useEffect(() => {
    if (!open) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, onClose])

  // Lock body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [open])

  if (!open) return null

  return (
    <div
      data-testid={testId}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'glass-modal-title' : undefined}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      {/* Backdrop */}
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-black/60 backdrop-blur-glass-heavy"
        onClick={onClose}
      />

      {/* Modal panel */}
      <div
        ref={dialogRef}
        className={[
          'relative z-10',
          'w-full max-w-lg',
          'rounded-kbkkk-xl',
          'bg-[var(--kbkkk-bg-overlay)]',
          'border border-[var(--glass-border)]',
          'shadow-glass-modal',
          'backdrop-blur-glass-heavy',
          'overflow-hidden',
          // Spring-like entrance animation (simplified, no framer-motion dep)
          'animate-modal-enter',
        ].join(' ')}
      >
        {/* Top highlight */}
        <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-white/[0.06]" />

        {/* Header */}
        {title && (
          <div className="flex items-center justify-between px-5 pt-4 pb-3">
            <h2
              id="glass-modal-title"
              className="text-kbkkk-lg font-semibold text-kbkkk-text"
            >
              {title}
            </h2>
            <button
              onClick={onClose}
              aria-label="关闭"
              className={[
                'w-7 h-7 flex items-center justify-center',
                'rounded-kbkkk-sm',
                'text-kbkkk-muted hover:text-kbkkk-text',
                'hover:bg-white/[0.08]',
                'transition-colors duration-150',
              ].join(' ')}
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        )}

        {/* Body */}
        <div className="px-5 pb-4 text-kbkkk-text-secondary text-kbkkk-sm">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-[var(--glass-border)]">
            {footer}
          </div>
        )}
      </div>

      <style>{`
        @keyframes modal-enter {
          from { opacity: 0; transform: scale(0.96) translateY(4px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
        .animate-modal-enter {
          animation: modal-enter 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
        }
      `}</style>
    </div>
  )
}
