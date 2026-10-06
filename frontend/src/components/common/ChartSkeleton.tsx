/** 图表骨架屏（macOS 毛玻璃风格） */
const HEIGHTS = [45, 60, 55, 70, 65, 80, 75, 60, 85, 70, 90, 75, 80, 65, 95, 80, 70, 60, 75, 55]

export function ChartSkeleton() {
  return (
    <div
      data-testid="chart-skeleton"
      className="w-full h-full flex items-center justify-center"
      aria-label="加载中"
      role="status"
    >
      <div className="flex flex-col items-center gap-3">
        {/* 模拟 K 线骨架（高度用固定值，非 Math.random 避免 lint purity warning） */}
        <div className="flex items-end gap-1 h-16">
          {HEIGHTS.map((h, i) => (
            <div
              key={i}
              className="w-1.5 bg-gray-300 dark:bg-gray-600 rounded-sm animate-pulse"
              style={{ height: `${h}%`, animationDelay: `${i * 50}ms` }}
            />
          ))}
        </div>
        <span className="text-sm text-gray-400 dark:text-gray-500 animate-pulse">
          加载 K 线数据...
        </span>
      </div>
    </div>
  )
}
