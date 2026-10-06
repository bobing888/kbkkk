/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class', // manual dark mode via .dark class on <html>
  theme: {
    extend: {
      // ─── Color tokens (macOS Sonoma dark palette) ────────────────────────
      colors: {
        // Background
        'kbkkk-bg': '#0d0e10',
        'kbkkk-bg-elevated': '#13151a',
        'kbkkk-bg-overlay': '#1a1d24',
        // Surface
        'kbkkk-surface': '#16181c',
        'kbkkk-surface-hover': '#1c1f25',
        'kbkkk-surface-active': '#22252c',
        // Text
        'kbkkk-text': '#e7e9ea',
        'kbkkk-text-secondary': '#b0b5be',
        'kbkkk-muted': '#71767b',
        // Border
        'kbkkk-border': '#2a2d35',
        'kbkkk-border-strong': '#3d414a',
        // Accent (BTC orange)
        'kbkkk-accent': '#f7931a',
        'kbkkk-accent-hover': '#ffaa33',
        'kbkkk-accent-muted': 'rgba(247,147,26,0.15)',
        // Success (crypto green)
        'kbkkk-success': '#16c784',
        'kbkkk-success-muted': 'rgba(22,199,132,0.15)',
        // Danger (crypto red)
        'kbkkk-danger': '#ea3943',
        'kbkkk-danger-muted': 'rgba(234,57,67,0.15)',
      },

      // ─── Border radius ───────────────────────────────────────────────────
      borderRadius: {
        'kbkkk-sm': '4px',
        'kbkkk-md': '8px',
        'kbkkk-lg': '12px',
        'kbkkk-xl': '16px',
        'kbkkk-2xl': '24px',
      },

      // ─── Spacing ─────────────────────────────────────────────────────────
      spacing: {
        'kbkkk-xs': '8px',
        'kbkkk-sm': '12px',
        'kbkkk-md': '16px',
        'kbkkk-lg': '20px',
        'kbkkk-xl': '24px',
        'kbkkk-2xl': '32px',
      },

      // ─── Font size ───────────────────────────────────────────────────────
      fontSize: {
        'kbkkk-xs': '11px',
        'kbkkk-sm': '13px',
        'kbkkk-base': '15px',
        'kbkkk-lg': '17px',
        'kbkkk-xl': '20px',
        'kbkkk-2xl': '24px',
        'kbkkk-3xl': '32px',
      },

      // ─── Backdrop blur ───────────────────────────────────────────────────
      backdropBlur: {
        'glass': '20px',
        'glass-heavy': '40px',
        'glass-light': '12px',
      },

      // ─── Box shadow (glass depth) ───────────────────────────────────────
      boxShadow: {
        'glass': '0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06)',
        'glass-hover': '0 12px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08)',
        'glass-modal': '0 24px 64px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.06)',
      },

      // ─── Animation (spring defaults) ─────────────────────────────────────
      transitionDuration: {
        'spring': '200ms',
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      },
    },
  },
  plugins: [],
}
