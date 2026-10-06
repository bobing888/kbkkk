/** KBKKK 主页 - 阶段 2
 *  - 顶部：symbol/period/market 选择器
 *  - 主体：3 个 tab = K线 + 指标 / 形态 / 信号
 *  - 数据：tanstack-query 调 4 个后端端点
 */
import { useState } from 'react'
import { useKLineData } from './hooks/useKlineData'
import {
  useIndicators,
  usePatterns,
  useSignals,
  useAnalysis,
} from './hooks/useAnalysis'
import { KLineChart } from './components/KLineChart'
import { ChartSkeleton } from './components/common/ChartSkeleton'
import { ErrorMessage } from './components/common/ErrorMessage'
import { EmptyState } from './components/common/EmptyState'
import type { Period, Market } from './api/klineApi'
import './App.css'

type TabKey = 'analysis' | 'patterns' | 'signals' | 'indicators'

const SYMBOL_PRESETS: { symbol: string; market: Market; label: string }[] = [
  { symbol: 'BTC', market: 'crypto', label: 'BTC/USDT' },
  { symbol: 'ETH', market: 'crypto', label: 'ETH/USDT' },
  { symbol: 'SOL', market: 'crypto', label: 'SOL/USDT' },
]

const PERIOD_OPTIONS: Period[] = ['1d', '1w', '60m', '30m', '15m']

function App() {
  const [symbol, setSymbol] = useState('BTC')
  const [market] = useState<Market>('crypto')
  const [period, setPeriod] = useState<Period>('1d')
  const [tab, setTab] = useState<TabKey>('analysis')

  // K线
  const kline = useKLineData({ symbol, period, market })
  // 分析（聚合）
  const analysis = useAnalysis(symbol, period, market)
  // 单独端点（用于其他 tab）
  const indicators = useIndicators(symbol, period, market)
  const patterns = usePatterns(symbol, period, market, 30)
  const signals = useSignals(symbol, period, market)

  return (
    <div className="kbkkk-app">
      <header className="kbkkk-header">
        <h1>KBKKK</h1>
        <p className="kbkkk-subtitle">K线趋势分析系统 · BTC/ETH 专用</p>
      </header>

      {/* 控件栏 */}
      <div className="kbkkk-controls">
        <div className="control-group">
          <label>标的</label>
          <div className="preset-buttons">
            {SYMBOL_PRESETS.map((p) => (
              <button
                key={p.symbol}
                className={symbol === p.symbol ? 'preset-btn active' : 'preset-btn'}
                onClick={() => setSymbol(p.symbol)}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <label>周期</label>
          <select value={period} onChange={(e) => setPeriod(e.target.value as Period)}>
            {PERIOD_OPTIONS.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label>分析</label>
          <div className="preset-buttons">
            {(['analysis', 'indicators', 'patterns', 'signals'] as TabKey[]).map((t) => (
              <button
                key={t}
                className={tab === t ? 'preset-btn active' : 'preset-btn'}
                onClick={() => setTab(t)}
              >
                {t === 'analysis' ? '聚合' : t === 'indicators' ? '指标' : t === 'patterns' ? '形态' : '信号'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* K线图 */}
      <section className="kbkkk-chart-section">
        <h2>{symbol}/{market === 'crypto' ? 'USDT' : market.toUpperCase()} · {period}</h2>
        {kline.isLoading && <ChartSkeleton />}
        {kline.error && <ErrorMessage message={kline.error.message} />}
        {kline.data && kline.data.data.length === 0 && <EmptyState message="无 K 线数据" />}
        {kline.data && kline.data.data.length > 0 && (
          <KLineChart symbol={symbol} data={kline.data.data} />
        )}
        {kline.data && (
          <div className="kbkkk-source-tag">
            来源: {kline.data.source} · {kline.data.data.length} 根 K 线
          </div>
        )}
      </section>

      {/* Tab 面板 */}
      <section className="kbkkk-panel">
        {tab === 'analysis' && (
          <AnalysisPanel
            loading={analysis.isLoading}
            error={analysis.error as Error | null}
            data={analysis.data}
          />
        )}
        {tab === 'indicators' && (
          <IndicatorsPanel
            loading={indicators.isLoading}
            error={indicators.error as Error | null}
            data={indicators.data}
          />
        )}
        {tab === 'patterns' && (
          <PatternsPanel
            loading={patterns.isLoading}
            error={patterns.error as Error | null}
            data={patterns.data}
          />
        )}
        {tab === 'signals' && (
          <SignalsPanel
            loading={signals.isLoading}
            error={signals.error as Error | null}
            data={signals.data}
          />
        )}
      </section>

      <footer className="kbkkk-footer">
        <span>API: {import.meta.env.VITE_API_BASE}</span>
        <span>·</span>
        <span>v0.1.0</span>
      </footer>
    </div>
  )
}

// ─── 4 个面板组件 ──────────────────────────────────────────────────────

function AnalysisPanel({
  loading, error, data,
}: { loading: boolean; error: Error | null; data: ReturnType<typeof useAnalysis>['data'] }) {
  if (loading) return <ChartSkeleton />
  if (error) return <ErrorMessage message={error.message} />
  if (!data) return <EmptyState message="无数据" />

  return (
    <div className="panel-content">
      <h3>指标概览</h3>
      <IndicatorsGrid data={data.indicators} />
      <h3>形态 ({data.patterns.length})</h3>
      <PatternsTable patterns={data.patterns.slice(0, 10)} />
      <h3>信号 ({data.signals.length})</h3>
      <SignalsList signals={data.signals} />
    </div>
  )
}

function IndicatorsPanel({
  loading, error, data,
}: { loading: boolean; error: Error | null; data: ReturnType<typeof useIndicators>['data'] }) {
  if (loading) return <ChartSkeleton />
  if (error) return <ErrorMessage message={error.message} />
  if (!data) return <EmptyState message="无数据" />
  return (
    <div className="panel-content">
      <h3>技术指标</h3>
      <IndicatorsGrid data={data.indicators} />
    </div>
  )
}

function PatternsPanel({
  loading, error, data,
}: { loading: boolean; error: Error | null; data: ReturnType<typeof usePatterns>['data'] }) {
  if (loading) return <ChartSkeleton />
  if (error) return <ErrorMessage message={error.message} />
  if (!data) return <EmptyState message="无数据" />
  return (
    <div className="panel-content">
      <h3>K线形态 ({data.count})</h3>
      <PatternsTable patterns={data.patterns} />
    </div>
  )
}

function SignalsPanel({
  loading, error, data,
}: { loading: boolean; error: Error | null; data: ReturnType<typeof useSignals>['data'] }) {
  if (loading) return <ChartSkeleton />
  if (error) return <ErrorMessage message={error.message} />
  if (!data) return <EmptyState message="无数据" />
  return (
    <div className="panel-content">
      <h3>交易信号 ({data.count})</h3>
      {data.count === 0 ? (
        <EmptyState message="当前无共振信号（趋势不明确或 ADX < 25）" />
      ) : (
        <SignalsList signals={data.signals} />
      )}
    </div>
  )
}

// ─── 通用展示组件 ──────────────────────────────────────────────────────

function IndicatorsGrid({ data }: { data: NonNullable<ReturnType<typeof useIndicators>['data']>['indicators'] }) {
  const fmt = (v: number | undefined) => v == null ? '—' : v.toFixed(2)
  return (
    <div className="indicators-grid">
      <div className="indicator-card">
        <h4>MA 均线</h4>
        <dl>
          <dt>MA5</dt><dd>{fmt(data.MA?.MA5)}</dd>
          <dt>MA10</dt><dd>{fmt(data.MA?.MA10)}</dd>
          <dt>MA20</dt><dd>{fmt(data.MA?.MA20)}</dd>
          <dt>MA60</dt><dd>{fmt(data.MA?.MA60)}</dd>
          <dt>MA120</dt><dd>{fmt(data.MA?.MA120)}</dd>
          <dt>MA250</dt><dd>{fmt(data.MA?.MA250)}</dd>
        </dl>
      </div>
      <div className="indicator-card">
        <h4>MACD</h4>
        <dl>
          <dt>DIF</dt><dd>{fmt(data.MACD?.DIF)}</dd>
          <dt>DEA</dt><dd>{fmt(data.MACD?.DEA)}</dd>
          <dt>MACD</dt><dd>{fmt(data.MACD?.MACD)}</dd>
        </dl>
      </div>
      <div className="indicator-card">
        <h4>RSI</h4>
        <p className="big-value">{fmt(data.RSI)}</p>
        <p className="hint">
          {data.RSI != null && (data.RSI > 70 ? '超买' : data.RSI < 30 ? '超卖' : '中性')}
        </p>
      </div>
      <div className="indicator-card">
        <h4>布林带</h4>
        <dl>
          <dt>上轨</dt><dd>{fmt(data.BOLL?.BOLL_UPPER)}</dd>
          <dt>中轨</dt><dd>{fmt(data.BOLL?.BOLL_MID)}</dd>
          <dt>下轨</dt><dd>{fmt(data.BOLL?.BOLL_LOWER)}</dd>
        </dl>
      </div>
      <div className="indicator-card">
        <h4>KDJ</h4>
        <dl>
          <dt>K</dt><dd>{fmt(data.KDJ?.K)}</dd>
          <dt>D</dt><dd>{fmt(data.KDJ?.D)}</dd>
          <dt>J</dt><dd>{fmt(data.KDJ?.J)}</dd>
        </dl>
      </div>
      <div className="indicator-card">
        <h4>OBV</h4>
        <p className="big-value">{data.OBV == null ? '—' : Math.round(data.OBV).toLocaleString()}</p>
      </div>
    </div>
  )
}

function PatternsTable({ patterns }: { patterns: Array<{ datetime: string; name: string; open: number; high: number; low: number; close: number }> }) {
  if (patterns.length === 0) return <EmptyState message="最近 30 根 K 线无形态命中" />
  return (
    <table className="kbkkk-table">
      <thead>
        <tr>
          <th>时间</th>
          <th>形态</th>
          <th>开</th>
          <th>高</th>
          <th>低</th>
          <th>收</th>
        </tr>
      </thead>
      <tbody>
        {patterns.map((p, i) => (
          <tr key={i}>
            <td>{p.datetime.slice(0, 10)}</td>
            <td><code>{p.name}</code></td>
            <td>{p.open.toFixed(2)}</td>
            <td>{p.high.toFixed(2)}</td>
            <td>{p.low.toFixed(2)}</td>
            <td>{p.close.toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function SignalsList({ signals }: { signals: Array<{ name: string; direction: string; confidence: number; entry?: number; stop_loss?: number; take_profit?: number; datetime?: string }> }) {
  return (
    <ul className="signals-list">
      {signals.map((s, i) => (
        <li key={i} className={`signal-item signal-${s.direction}`}>
          <div className="signal-header">
            <strong>{s.name}</strong>
            <span className={`direction-badge direction-${s.direction}`}>
              {s.direction === 'long' ? '做多' : s.direction === 'short' ? '做空' : '中性'}
            </span>
            <span className="confidence">置信度 {(s.confidence * 100).toFixed(0)}%</span>
          </div>
          <div className="signal-prices">
            {s.entry != null && <span>入场 {s.entry.toFixed(2)}</span>}
            {s.stop_loss != null && <span className="sl">止损 {s.stop_loss.toFixed(2)}</span>}
            {s.take_profit != null && <span className="tp">止盈 {s.take_profit.toFixed(2)}</span>}
            {s.datetime && <span className="ts">{s.datetime}</span>}
          </div>
        </li>
      ))}
    </ul>
  )
}

export default App
