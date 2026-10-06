/**
 * SettingsPage — 设置页
 * M3 3.1: 外观 + 数据源 + 关于
 */
import { useState } from 'react'
import { GlassCard } from '../components/ui/GlassCard'
import { GlassSegmented } from '../components/ui/GlassSegmented'
import { useUIStore } from '../store'
import type { Theme } from '../store'

const THEME_OPTIONS: { value: Theme; label: string }[] = [
  { value: 'dark', label: '暗色' },
  { value: 'light', label: '亮色' },
  { value: 'system', label: '系统' },
]

const EXCHANGE_OPTIONS = [
  { value: 'okx', label: 'OKX' },
  { value: 'binance', label: 'Binance' },
] as const

export function SettingsPage() {
  const { theme, setTheme } = useUIStore()
  const [exchange] = useState<typeof EXCHANGE_OPTIONS[number]['value']>('okx')

  return (
    <div data-testid="settings-page" className="space-y-4">
      {/* 页面标题 */}
      <div className="pt-2 pb-1">
        <h1 className="text-xl font-semibold text-kbkkk-text">设置</h1>
        <p className="text-sm text-kbkkk-muted mt-0.5">
          外观、数据源、版本信息
        </p>
      </div>

      {/* 外观设置 */}
      <GlassCard padding="sm">
        <div className="space-y-3">
          <div>
            <p className="text-xs text-kbkkk-muted mb-2 uppercase tracking-wider">外观</p>
            <GlassSegmented
              options={THEME_OPTIONS}
              value={theme}
              onChange={(val) => {
                const v = Array.isArray(val) ? val[0] : val
                setTheme(v as Theme)
              }}
              data-testid="theme-selector"
            />
          </div>
        </div>
      </GlassCard>

      {/* 数据源设置 */}
      <GlassCard padding="sm">
        <div className="space-y-3">
          <div>
            <p className="text-xs text-kbkkk-muted mb-2 uppercase tracking-wider">数据源</p>
            <GlassSegmented
              options={[...EXCHANGE_OPTIONS]}
              value={exchange}
              onChange={() => {}}
              data-testid="exchange-selector"
            />
          </div>
        </div>
      </GlassCard>

      {/* 关于区块 */}
      <GlassCard padding="sm">
        <div className="space-y-2">
          <p className="text-xs text-kbkkk-muted uppercase tracking-wider">关于</p>
          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <span className="text-sm text-kbkkk-secondary">版本</span>
              <span className="text-sm text-kbkkk-text">v0.3.0</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-kbkkk-secondary">数据</span>
              <span className="text-sm text-kbkkk-text">BTC / ETH</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-kbkkk-secondary">许可证</span>
              <span className="text-sm text-kbkkk-muted">MIT</span>
            </div>
          </div>
        </div>
      </GlassCard>
    </div>
  )
}
