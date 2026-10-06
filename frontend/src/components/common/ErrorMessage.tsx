interface ErrorMessageProps {
  message: string
}

/** 图表错误态 */
export function ErrorMessage({ message }: ErrorMessageProps) {
  return (
    <div
      data-testid="error-message"
      className="w-full h-full flex items-center justify-center"
      role="alert"
    >
      <div className="text-center space-y-1">
        <p className="text-red-500 dark:text-red-400 text-sm font-medium">
          ⚠️ {message}
        </p>
        <p className="text-gray-400 text-xs">
          请检查网络或联系管理员
        </p>
      </div>
    </div>
  )
}
