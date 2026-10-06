import '@testing-library/jest-dom'
import ResizeObserver from 'resize-observer-polyfill'

declare const global: typeof globalThis & {
  ResizeObserver: typeof ResizeObserver
}
global.ResizeObserver = ResizeObserver
