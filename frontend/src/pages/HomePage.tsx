/**
 * HomePage — 首页（K线 + 指标总览）
 * M3 3.2: 升级为真实 KLineChart 主图（WebGL 10k 50fps）
 *
 * BTC/ETH only（V2 §1 强制）
 * 暗色强制（V2 §3.0 不变量）
 */
import { useSymbolStore } from '../store'
import { useKLineData } from '../hooks/useKlineData'
import { usePatterns } from '../hooks/useAnalysis'
import { useSignals } from '../hooks/useAnalysis'
import { GlassCard } from '../components/ui/GlassCard'
import { GlassSegmented } from '../components/ui/GlassSegmented'
import { KLineChart } from '../components/KLineChart/index'

const SYMBOL_OPTIONS = [
  { value: 'BTC', label: 'BTC' },
  { value: 'ETH', label: 'ETH' },
] as const

const PERIOD_OPTIONS = [
  { value: '1d', label: '1d' },
  { value: '1w', label: '1w' },
  { value: '4h', label: '4h' },
  { value: '60m', label: '60m' },
  { value: '30m', label: '30m' },
  { value: '15m', label: '15m' },
] as const

const INDICATOR_NAMES = ['MACD', 'KDJ', 'RSI', '布林带'] as const

export function HomePage() {
  const { symbol, period, market, setSymbol, setPeriod } = useSymbolStore()

  // ── K线数据（TanStack Query，5 min staleTime）────────────────────────────
  const klineQuery = useKLineData({ symbol, period, market })
  // ── Patterns（用于 markers，V2 §10 #8）────────────────────────────────
  const patternsQuery = usePatterns(symbol, period, market, 30)
  // ── Signals（用于 markers，V2 §10 #8）─────────────────────────────────
  const signalsQuery = useSignals(symbol, period, market)

  // symbol 变化时同步到 store
  const handleSymbolChange = (val: string | string[]) => {
    const v = Array.isArray(val) ? val[0] : val
    setSymbol(v)
  }

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

      {/* symbol + period 选择器 */}
      <GlassCard padding="sm">
        <div className="space-y-3">
          <div>
            <p className="text-xs text-kbkkk-muted mb-2 uppercase tracking-wider">标的</p>
            <GlassSegmented
              options={[...SYMBOL_OPTIONS]}
              value={symbol}
              onChange={handleSymbolChange}
              data-testid="symbol-selector"
            />
          </div>

          <div>
            <p className="text-xs text-kbkkk-muted mb-2 uppercase tracking-wider">周期</p>
            <GlassSegmented
              options={[...PERIOD_OPTIONS]}
              value={period}
              onChange={(val) => {
                const v = Array.isArray(val) ? val[0] : val
                setPeriod(v as typeof PERIOD_OPTIONS[number]['value'])
              }}
              data-testid="period-selector"
            />
          </div>
        </div>
      </GlassCard>

      {/* K线主图（3.2 升级为真实图表）—— V2 §3.2 强制 */}
      <GlassCard padding="none" className="overflow-hidden">
        <div className="h-[480px]">
          <KLineChart
            symbol={`${symbol}/USDT`}
            data={klineQuery.data?.data ?? []}
            loading={klineQuery.isLoading}
            error={klineQuery.isError ? '加载 K 线数据失败' : null}
            patterns={patternsQuery.data?.patterns}
            signals={signalsQuery.data?.signals}
          />
        </div>
      </GlassCard>

      {/* 4 个核心指标卡（stub，M3.3 接入真实指标） */}
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
