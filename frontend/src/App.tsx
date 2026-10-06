/**
 * KBKKK 主页 — 路由驱动版本
 *
 * App.tsx 现在由 router.tsx 驱动（react-router-dom v7 BrowserRouter）
 * 保留 hooks 导出以维持向后兼容
 *
 * M3 3.1: 4 tab 旧结构 → <Outlet/> + 路由驱动
 */
import { useKLineData } from './hooks/useKlineData'
import {
  useIndicators,
  usePatterns,
  useSignals,
  useAnalysis,
} from './hooks/useAnalysis'

// ─── 向后兼容：保留所有原有 hooks 导出 ─────────────────────────────────
// 其他模块依赖这些 hooks，删除会破坏构建
export { useKLineData, useIndicators, usePatterns, useSignals, useAnalysis }

// 默认导出保留（某些工具可能依赖）
export default function App() {
  // 路由已在 main.tsx 通过 RouterProvider 驱动
  // 此组件现在仅用于保留 hooks 导出
  return null
}
