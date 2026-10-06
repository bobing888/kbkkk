/**
 * useResizeObserver — 容器 resize 监听 hook
 * M3 3.2：K 线主图自动响应式 resize
 * License: Original work for kbkkk project.
 */
import { useEffect, useRef, useCallback } from 'react'

interface Size {
  width: number
  height: number
}

interface UseResizeObserverOptions {
  /** 触发 resize 时回调 */
  onResize: (size: Size) => void
  /** 是否立即触发一次初始尺寸 */
  immediate?: boolean
}

/**
 * 订阅容器 ResizeObserver，容器尺寸变化时调用 onResize。
 * cleanup 时 disconnect。
 */
export function useResizeObserver(
  ref: React.RefObject<HTMLElement | null>,
  { onResize, immediate = true }: UseResizeObserverOptions,
) {
  const onResizeRef = useRef(onResize)
  onResizeRef.current = onResize

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const handleResize = useCallback((entries: ResizeObserverEntry[]) => {
    const entry = entries[0]
    if (!entry) return
    onResizeRef.current({
      width: entry.contentRect.width,
      height: entry.contentRect.height,
    })
  }, [])

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new ResizeObserver(handleResize)
    observer.observe(el)

    // 立即触发一次初始尺寸
    if (immediate) {
      onResizeRef.current({
        width: el.clientWidth,
        height: el.clientHeight,
      })
    }

    return () => {
      observer.disconnect()
    }
  }, [ref, handleResize, immediate])
}
