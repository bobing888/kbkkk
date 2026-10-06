interface EmptyStateProps {
  message?: string
}

/** 图表空数据态 */
export function EmptyState({ message = '暂无数据' }: EmptyStateProps) {
  return (
    <div className="w-full h-full flex items-center justify-center">
      <p className="text-gray-400 text-sm">{message}</p>
    </div>
  )
}
