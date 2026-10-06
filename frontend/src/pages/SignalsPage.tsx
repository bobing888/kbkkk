/**
 * SignalsPage — 信号中心
 * M3 3.1: 实时信号流 + 信号详情（占位，3.4 实现完整版）
 */
import { GlassCard } from '../components/ui/GlassCard'

export function SignalsPage() {
  return (
    <div data-testid="signals-page" className="space-y-4">
      {/* 页面标题 */}
      <div className="pt-2 pb-1">
        <h1 className="text-xl font-semibold text-kbkkk-text">信号中心</h1>
        <p className="text-sm text-kbkkk-muted mt-0.5">
          实时共振信号 · BTC/ETH
        </p>
      </div>

      {/* 信号统计 */}
      <GlassCard padding="sm">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-kbkkk-muted uppercase tracking-wider">当前信号</p>
            <p className="text-2xl font-bold text-kbkkk-text mt-0.5">0</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-kbkkk-muted uppercase tracking-wider">状态</p>
            <p className="text-sm text-kbkkk-success mt-0.5">监测中</p>
          </div>
        </div>
      </GlassCard>

      {/* 信号列表占位 */}
      <GlassCard padding="lg">
        <div className="h-48 flex items-center justify-center">
          <div className="text-center text-kbkkk-muted">
            <div className="text-4xl mb-2">🔔</div>
            <p className="text-sm">实时信号流（3.4 实现）</p>
            <p className="text-xs mt-1 opacity-60">ADX ≥ 25 时触发</p>
          </div>
        </div>
      </GlassCard>
    </div>
  )
}
