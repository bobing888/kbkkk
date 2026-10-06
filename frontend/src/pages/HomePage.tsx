/**
 * HomePage — 首页（K线 + 指标总览）
 * M3 3.1: symbol/period/market 选择器 + K线主图占位 + 4 个核心指标卡
 *
 * BTC/ETH only（V2 §1 强制）
 * 暗色强制（V2 §3.0 不变量）
 */
import { useState } from 'react'
import { GlassCard } from '../components/ui/GlassCard'
import { GlassSegmented } from '../components/ui/GlassSegmented'
import { useSymbolStore } from '../store'
import type { Period, Market } from '../api/klineApi'

const SYMBOL_OPTIONS = [
  { value: 'BTC', label: 'BTC' },
  { value: 'ETH', label: 'ETH' },
] as const

const PERIOD_OPTIONS: Period[] = ['1d', '1w', '4h', '60m', '30m', '15m']

const INDICATOR_NAMES = ['MACD', 'KDJ', 'RSI', '布林带'] as const

export function HomePage() {
  const { symbol, period, market, setSymbol, setPeriod } = useSymbolStore()
  const [activeSymbol] = useState<'BTC' | 'ETH'>('BTC')

  return (
    <div data-testid="home-page" className="space-y-4">
      {/* 页面标题 */}
      <div className="pt-2 pb-1">
        <h1 className="text-xl font-semibold text-kbkkk-text">
          {symbol}/USDT · {period}
        </h1>
        <p className="text-sm text-kbkkk-muted mt-0.5">
          K线趋势分析 · BTC/ETH 专用
        </p>
      </div>

      {/* symbol 选择器 */}
      <GlassCard padding="sm">
        <div className="space-y-3">
          <div>
            <p className="text-xs text-kbkkk-muted mb-2 uppercase tracking-wider">标的</p>
            <GlassSegmented
              options={[...SYMBOL_OPTIONS]}
              value={activeSymbol}
              onChange={(val) => {
                const v = Array.isArray(val) ? val[0] : val
                setSymbol(v as 'BTC' | 'ETH')
              }}
              data-testid="symbol-selector"
            />
          </div>

          <div>
            <p className="text-xs text-kbkkk-muted mb-2 uppercase tracking-wider">周期</p>
            <div className="flex flex-wrap gap-1">
              {PERIOD_OPTIONS.map((p) => (
                <button
                  key={p}
                  data-testid={`period-${p}`}
                  className={[
                    'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                    period === p
                      ? 'bg-[var(--accent,#f7931a)] text-black'
                      : 'bg-[rgba(255,255,255,0.06)] text-kbkkk-secondary hover:bg-[rgba(255,255,255,0.10)]',
                  ].join(' ')}
                  onClick={() => setPeriod(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      </GlassCard>

      {/* K线主图占位（3.2 升级为真实图表） */}
      <GlassCard padding="lg">
        <div className="h-64 flex items-center justify-center">
          <div className="text-center text-kbkkk-muted">
            <div className="text-4xl mb-2">📈</div>
            <p className="text-sm">K线图表（3.2 实现）</p>
            <p className="text-xs mt-1 opacity-60">{symbol}/USDT · {period}</p>
          </div>
        </div>
      </GlassCard>

      {/* 4 个核心指标卡 */}
      <div>
        <p className="text-xs text-kbkkk-muted mb-2 uppercase tracking-wider">技术指标</p>
        <div className="grid grid-cols-2 gap-2">
          {INDICATOR_NAMES.map((name) => (
            <GlassCard key={name} padding="sm" hoverable>
              <div className="text-center">
                <p className="text-xs text-kbkkk-muted mb-1">{name}</p>
                <p className="text-lg font-semibold text-kbkkk-text">—</p>
              </div>
            </GlassCard>
          ))}
        </div>
      </div>
    </div>
  )
}
