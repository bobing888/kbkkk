/**
 * Glass component render tests — macOS Sonoma UI library
 * One render test per component to verify basic functionality.
 */
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { GlassCard } from '../components/ui/GlassCard'
import { GlassButton } from '../components/ui/GlassButton'
import { GlassSkeleton } from '../components/ui/GlassSkeleton'
import { GlassSegmented } from '../components/ui/GlassSegmented'
import { GlassModal } from '../components/ui/GlassModal'

// ─── GlassCard ─────────────────────────────────────────────────────────

describe('GlassCard', () => {
  it('renders children content', () => {
    render(<GlassCard data-testid="glass-card">Card Content</GlassCard>)
    expect(screen.getByTestId('glass-card')).toBeInTheDocument()
    expect(screen.getByText('Card Content')).toBeInTheDocument()
  })

  it('applies padding class', () => {
    const { container } = render(<GlassCard padding="lg">content</GlassCard>)
    expect(container.firstChild).toHaveClass('p-6')
  })

  it('passes data-testid', () => {
    render(<GlassCard data-testid="gc-test">text</GlassCard>)
    expect(screen.getByTestId('gc-test')).toBeInTheDocument()
  })
})

// ─── GlassButton ───────────────────────────────────────────────────────

describe('GlassButton', () => {
  it('renders button with children', () => {
    render(<GlassButton data-testid="glass-btn">Click Me</GlassButton>)
    expect(screen.getByTestId('glass-btn')).toBeInTheDocument()
    expect(screen.getByText('Click Me')).toBeInTheDocument()
  })

  it('renders primary variant', () => {
    const { container } = render(<GlassButton variant="primary">Primary</GlassButton>)
    // primary uses bg-kbkkk-accent/90
    expect(container.firstChild?.className).toContain('bg-kbkkk-accent')
  })

  it('calls onClick when clicked', () => {
    const handler = vi.fn()
    render(<GlassButton onClick={handler} data-testid="btn">Btn</GlassButton>)
    fireEvent.click(screen.getByTestId('btn'))
    expect(handler).toHaveBeenCalledOnce()
  })

  it('does not call onClick when disabled', () => {
    const handler = vi.fn()
    render(<GlassButton disabled onClick={handler} data-testid="btn-disabled">Disabled</GlassButton>)
    const btn = screen.getByTestId('btn-disabled')
    expect(btn).toBeDisabled()
    fireEvent.click(btn)
    expect(handler).not.toHaveBeenCalled()
  })
})

// ─── GlassSkeleton ─────────────────────────────────────────────────────

describe('GlassSkeleton', () => {
  it('renders skeleton with text variant', () => {
    render(<GlassSkeleton variant="text" data-testid="sk-text" />)
    expect(screen.getByTestId('sk-text')).toBeInTheDocument()
  })

  it('renders skeleton with chart variant', () => {
    render(<GlassSkeleton variant="chart" data-testid="sk-chart" label="加载中..." />)
    expect(screen.getByTestId('sk-chart')).toBeInTheDocument()
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('has role=status for accessibility', () => {
    render(<GlassSkeleton data-testid="sk" />)
    expect(screen.getByTestId('sk')).toHaveAttribute('role', 'status')
  })
})

// ─── GlassSegmented ────────────────────────────────────────────────────

describe('GlassSegmented', () => {
  const options = [
    { value: 'btc' as const, label: 'BTC' },
    { value: 'eth' as const, label: 'ETH' },
    { value: 'sol' as const, label: 'SOL' },
  ]

  it('renders all options', () => {
    render(
      <GlassSegmented
        options={options}
        value="btc"
        onChange={vi.fn()}
        data-testid="seg"
      />
    )
    expect(screen.getByText('BTC')).toBeInTheDocument()
    expect(screen.getByText('ETH')).toBeInTheDocument()
    expect(screen.getByText('SOL')).toBeInTheDocument()
  })

  it('calls onChange when option is selected', () => {
    const handler = vi.fn()
    render(
      <GlassSegmented
        options={options}
        value="btc"
        onChange={handler}
        data-testid="seg2"
      />
    )
    fireEvent.click(screen.getByText('ETH'))
    expect(handler).toHaveBeenCalledWith('eth')
  })

  it('supports multi-select mode', () => {
    const handler = vi.fn()
    render(
      <GlassSegmented
        options={options}
        value={['btc']}
        onChange={handler}
        multi
        data-testid="seg3"
      />
    )
    fireEvent.click(screen.getByText('ETH'))
    expect(handler).toHaveBeenCalled()
    const calledWith = handler.mock.calls[0][0]
    expect(calledWith).toContain('btc')
    expect(calledWith).toContain('eth')
  })
})

// ─── GlassModal ────────────────────────────────────────────────────────

describe('GlassModal', () => {
  it('renders when open', () => {
    render(
      <GlassModal open onClose={vi.fn()} title="Test Modal" data-testid="modal">
        Modal content here
      </GlassModal>
    )
    expect(screen.getByTestId('modal')).toBeInTheDocument()
    expect(screen.getByText('Test Modal')).toBeInTheDocument()
    expect(screen.getByText('Modal content here')).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    const { container } = render(
      <GlassModal open={false} onClose={vi.fn()} title="Hidden">hidden</GlassModal>
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('calls onClose when ESC is pressed', () => {
    const handler = vi.fn()
    render(
      <GlassModal open onClose={handler} title="ESC Test" data-testid="esc-modal">
        press esc
      </GlassModal>
    )
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(handler).toHaveBeenCalledOnce()
  })
})
