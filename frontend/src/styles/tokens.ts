/**
 * macOS Sonoma Design System Tokens
 *
 * Source: /opt/ai-trader/frontend/src/styles/tokens.ts (inspired, NOT copied)
 * License: This file is original work for kbkkk project, inspired by macOS Sonoma design language.
 *
 * macOS Sonoma design tokens covering:
 * - 7 color categories (background, surface, text, border, accent, success, danger)
 * - Border radius scale
 * - Spacing scale
 * - Font size scale
 * - Blur intensity for glass effects
 * - Spring physics for animations
 */

// ─── Color Palette ──────────────────────────────────────────────────────

export const colors = {
  /** Background layer — deepest z-index */
  background: {
    default: '#0d0e10',
    elevated: '#13151a',
    overlay: '#1a1d24',
  },
  /** Surface layer — cards, panels */
  surface: {
    default: '#16181c',
    hover: '#1c1f25',
    active: '#22252c',
    disabled: '#1a1d24',
  },
  /** Text hierarchy */
  text: {
    primary: '#e7e9ea',
    secondary: '#b0b5be',
    muted: '#71767b',
    placeholder: '#4a4f57',
    inverse: '#0d0e10',
  },
  /** Border / divider */
  border: {
    default: '#2a2d35',
    subtle: '#1f2228',
    strong: '#3d414a',
    focus: '#f7931a',
  },
  /** Accent — BTC orange primary brand color */
  accent: {
    default: '#f7931a',
    hover: '#ffaa33',
    active: '#d4820f',
    muted: 'rgba(247, 147, 26, 0.15)',
    text: '#f7931a',
  },
  /** Success — crypto green (bullish) */
  success: {
    default: '#16c784',
    hover: '#22d492',
    active: '#10a86c',
    muted: 'rgba(22, 199, 132, 0.15)',
    text: '#16c784',
  },
  /** Danger — crypto red (bearish) */
  danger: {
    default: '#ea3943',
    hover: '#f04d57',
    active: '#c72d37',
    muted: 'rgba(234, 57, 67, 0.15)',
    text: '#ea3943',
  },
} as const

// ─── Border Radius ───────────────────────────────────────────────────────

export const borderRadius = {
  /** 4px — tight UI elements */
  sm: '4px',
  /** 8px — buttons, inputs */
  md: '8px',
  /** 12px — cards, panels */
  lg: '12px',
  /** 16px — modals */
  xl: '16px',
  /** 24px — large containers */
  '2xl': '24px',
  /** Full pill shape */
  full: '9999px',
} as const

// ─── Spacing ─────────────────────────────────────────────────────────────

export const spacing = {
  /** 4px */
  xxs: '4px',
  /** 8px */
  xs: '8px',
  /** 12px */
  sm: '12px',
  /** 16px */
  md: '16px',
  /** 20px */
  lg: '20px',
  /** 24px */
  xl: '24px',
  /** 32px */
  '2xl': '32px',
  /** 40px */
  '3xl': '40px',
  /** 48px */
  '4xl': '48px',
} as const

// ─── Font Size ───────────────────────────────────────────────────────────

export const fontSize = {
  /** 11px — captions */
  xs: '11px',
  /** 13px — secondary labels */
  sm: '13px',
  /** 15px — body */
  base: '15px',
  /** 17px — subheadings */
  lg: '17px',
  /** 20px — headings */
  xl: '20px',
  /** 24px — page titles */
  '2xl': '24px',
  /** 32px — hero */
  '3xl': '32px',
} as const

// ─── Blur Intensity ───────────────────────────────────────────────────────

export const blur = {
  /** Glass card blur (macOS Sonoma standard) */
  glass: 20,
  /** Heavy blur for modals/overlays */
  heavy: 40,
  /** Light blur for subtle effects */
  light: 12,
} as const

// ─── Spring Physics ──────────────────────────────────────────────────────

/**
 * macOS-native spring feel.
 * damping: lower = more oscillation, higher = snappier settle
 * stiffness: higher = faster motion
 * mass: ~1 for natural feel
 */
export const spring = {
  /** Damping ratio (0-1). 0.8 = snappy with slight bounce */
  damping: 0.8,
  /** Stiffness (px/s). 200-300 = natural macOS feel */
  stiffness: 250,
  /** Mass multiplier. 1 = natural */
  mass: 1,
} as const

// ─── Glass Token ────────────────────────────────────────────────────────

/**
 * Glass effect token values.
 * Used with Tailwind backdrop-blur utilities + custom opacity layers.
 */
export const glass = {
  /** Glass surface color (semi-transparent) */
  bgLight: 'rgba(255, 255, 255, 0.08)',
  bgMedium: 'rgba(255, 255, 255, 0.12)',
  bgDark: 'rgba(255, 255, 255, 0.04)',
  /** Glass border */
  border: 'rgba(255, 255, 255, 0.12)',
  /** Glass highlight (top edge light) */
  highlight: 'rgba(255, 255, 255, 0.06)',
} as const

// ─── CSS Variables Export ─────────────────────────────────────────────────

/**
 * Convert tokens to CSS custom properties map.
 * Usage: inject into document.head or CSS file as --token-* variables.
 */
export function toCSSVars(prefix = 'kbkkk'): Record<string, string> {
  const vars: Record<string, string> = {}

  // Colors (flattened: category.key)
  const colorEntries = Object.entries(colors).flatMap(([cat, values]) =>
    Object.entries(values).map(([key, val]) => [`${prefix}-${cat}-${key}`, val])
  )
  colorEntries.forEach(([k, v]) => { vars[k] = v })

  // Blur
  Object.entries(blur).forEach(([k, v]) => { vars[`${prefix}-blur-${k}`] = `${v}px` })

  // Spring
  vars[`${prefix}-spring-damping`] = String(spring.damping)
  vars[`${prefix}-spring-stiffness`] = String(spring.stiffness)
  vars[`${prefix}-spring-mass`] = String(spring.mass)

  return vars
}
