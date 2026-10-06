/** @type {import('vitest').Config} */
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  define: {
    // 测试环境 VITE_API_BASE mock
    'import.meta.env.VITE_API_BASE': JSON.stringify('http://localhost:8000'),
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/setupTests.ts'],
    include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    tsconfig: './tsconfig.test.json',
  },
})
