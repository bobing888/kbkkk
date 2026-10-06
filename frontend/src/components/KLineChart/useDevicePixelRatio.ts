/**
 * useDevicePixelRatio — HiDPI 缩放比例 hook
 * M3 3.2：lightweight-charts v5 HiDPI 支持，1 万根 50 FPS
 * License: Original work for kbkkk project.
 */
import { useState } from 'react'

/** 获取当前 devicePixelRatio */
export function useDevicePixelRatio(): number {
  const [dpr] = useState(() => {
    if (typeof window !== 'undefined' && window.devicePixelRatio) {
      return window.devicePixelRatio
    }
    return 1
  })
  return dpr
}
