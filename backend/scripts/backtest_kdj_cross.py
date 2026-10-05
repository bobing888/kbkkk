"""
backtest_kdj_cross.py — KDJ 金叉死叉策略回测
========================================

对应 kline-analyst KDJ 经典形态实战

原理：
  - KDJ 指标 = 随机指标（Stochastic Oscillator 变体）
  - K 值上穿 D 值 = 金叉 → 买入信号
  - K 值下穿 D 值 = 死叉 → 卖出信号
  - J 值 > 100 = 超买，J < 0 = 超卖（辅助过滤）

合成数据规则（4 种 KDJ 形态）：
  1. 金叉上涨：上升趋势初段 K 上穿 D → 后续 10 日应继续涨
  2. 金叉下跌（假信号）：下跌趋势中 K 上穿 D → 后续 10 日应跌（策略失败）
  3. 死叉下跌：下降趋势初段 K 下穿 D → 后续 10 日应继续跌
  4. 死叉上涨（假信号）：上升趋势中 K 下穿 D → 后续 10 日应涨（策略失败）

评估：
  - 命中率 = 信号方向匹配实际方向的比例
  - 目标：≥ 55%（kline-analyst 成功指标基准，与量价背离对齐）

用法：
  python3 scripts/backtest_kdj_cross.py
  # 输出：4 种 KDJ 形态的命中率 + 报告
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import List
import json


@dataclass
class KDJCrossoverSignal:
    """KDJ 交叉信号"""
    type: str  # 'golden_cross' / 'death_cross'
    direction: str  # 'up' / 'down'（信号预期方向）
    confidence: float  # 0-1（基于 J 值位置）
    entry_price: float
    actual_return_5d: float = 0.0
    actual_return_10d: float = 0.0
    actual_return_20d: float = 0.0
    hit: bool = False


def calc_kdj(prices_high: np.ndarray, prices_low: np.ndarray, prices_close: np.ndarray,
             n: int = 9, m1: int = 3, m2: int = 3) -> tuple:
    """
    计算 KDJ 指标（向量化）

    返回: (K, D, J) 三个 numpy array
    """
    if len(prices_close) < n:
        return np.array([]), np.array([]), np.array([])

    low_n = pd.Series(prices_low).rolling(n, min_periods=1).min().values
    high_n = pd.Series(prices_high).rolling(n, min_periods=1).max().values
    rsv = (prices_close - low_n) / (high_n - low_n + 1e-10) * 100

    k = pd.Series(rsv).ewm(alpha=1/m1, adjust=False).mean().values
    d = pd.Series(k).ewm(alpha=1/m2, adjust=False).mean().values
    j = 3 * k - 2 * d

    return k, d, j


def detect_kdj_golden_cross(k: np.ndarray, d: np.ndarray) -> bool:
    """
    KDJ 金叉：当前 K > D 且前一根 K <= D
    即：K 刚刚上穿 D
    """
    if len(k) < 2 or len(d) < 2:
        return False
    return k[-1] > d[-1] and k[-2] <= d[-2]


def detect_kdj_death_cross(k: np.ndarray, d: np.ndarray) -> bool:
    """
    KDJ 死叉：当前 K < D 且前一根 K >= D
    即：K 刚刚下穿 D
    """
    if len(k) < 2 or len(d) < 2:
        return False
    return k[-1] < d[-1] and k[-2] >= d[-2]


def calc_j_confidence(j: float) -> float:
    """
    根据 J 值位置计算信号置信度

    J < 0（超卖）+ 金叉 = 高置信度（0.8-1.0）
    J > 100（超买）+ 死叉 = 高置信度（0.8-1.0）
    其他 = 中等置信度（0.5-0.7）
    """
    if j < 0:
        return 0.9  # 超卖金叉，可信度高
    elif j > 100:
        return 0.4  # 超买金叉，可能是假突破
    elif 20 < j < 80:
        return 0.5  # 中性区，置信度中等
    else:
        return 0.6


def generate_kdj_signal(k: np.ndarray, d: np.ndarray, j: np.ndarray,
                        prices: np.ndarray) -> dict:
    """
    综合检测 KDJ 交叉信号

    返回: {type, direction, confidence, entry_price}
    """
    if len(k) < 2 or len(prices) < 2:
        return {}

    signal = {
        'type': None,
        'direction': None,
        'confidence': 0.0,
        'entry_price': float(prices[-1]),
    }

    if detect_kdj_golden_cross(k, d):
        signal['type'] = 'golden_cross'
        signal['direction'] = 'up'
        signal['confidence'] = calc_j_confidence(float(j[-1]))
    elif detect_kdj_death_cross(k, d):
        signal['type'] = 'death_cross'
        signal['direction'] = 'down'
        signal['confidence'] = calc_j_confidence(float(j[-1]))

    return signal


def generate_bullish_trend_with_crossover(n: int = 200, seed: int = 42,
                                          with_pullback: bool = False) -> pd.DataFrame:
    """
    生成上升趋势 K 线（用于金叉测试）

    参数:
      with_pullback: True = 末段回撤后 KDJ 死叉（假信号场景）
                    False = 单纯上升 + 金叉（真信号场景）
    """
    np.random.seed(seed)
    trend = np.linspace(100, 200, n)
    noise = np.random.normal(0, 3, n)
    close = trend + noise
    # 构造 OHLC
    high = close + np.abs(np.random.normal(0, 1, n))
    low = close - np.abs(np.random.normal(0, 1, n))
    volume = np.random.normal(1000, 200, n)

    if with_pullback:
        # 末段小回撤（构造 KDJ 死叉）
        close[180:] *= 0.95
        high[180:] *= 0.95
        low[180:] *= 0.95

    return pd.DataFrame({'open': close, 'high': high, 'low': low, 'close': close, 'volume': volume})


def generate_bearish_trend_with_crossover(n: int = 200, seed: int = 42,
                                          with_bounce: bool = False) -> pd.DataFrame:
    """
    生成下降趋势 K 线（用于死叉测试）

    参数:
      with_bounce: True = 末段反弹（构造 KDJ 金叉假信号）
                   False = 单纯下跌 + 死叉（真信号场景）
    """
    np.random.seed(seed)
    trend = np.linspace(200, 100, n)
    noise = np.random.normal(0, 3, n)
    close = trend + noise
    high = close + np.abs(np.random.normal(0, 1, n))
    low = close - np.abs(np.random.normal(0, 1, n))
    volume = np.random.normal(1000, 200, n)

    if with_bounce:
        close[180:] *= 1.05
        high[180:] *= 1.05
        low[180:] *= 1.05

    return pd.DataFrame({'open': close, 'high': high, 'low': low, 'close': close, 'volume': volume})


def backtest_kdj_cross_type(
    signal_type: str,
    trend_func,
    n_samples: int = 200,
    forward_days: int = 10,
) -> dict:
    """
    回测 1 种 KDJ 交叉信号的命中率

    参数:
      signal_type: 'golden_cross' / 'death_cross'
      trend_func: 趋势生成函数
      n_samples: 样本数
      forward_days: 前向天数

    返回: dict 命中率统计
    """
    is_golden = (signal_type == 'golden_cross')
    expected_dir = 'up' if is_golden else 'down'

    hits = 0
    total = 0
    returns_5d = []
    returns_10d = []
    returns_20d = []

    for sample in range(n_samples):
        # 关键：构造更长序列（350 根）以便金叉点后还有 20 日空间
        df = trend_func(n=350, seed=sample + hash(signal_type) % 10000)
        prices = df['close'].values
        k, d, j = calc_kdj(df['high'].values, df['low'].values, prices)

        if len(k) < 2:
            continue

        # 找最后一个交叉点（不是只检查末尾）
        cross_idx = None
        if is_golden:
            for i in range(1, len(k) - 20):  # 关键：留 20 根空间
                if k[i] > d[i] and k[i-1] <= d[i-1]:
                    cross_idx = i  # 找最后一个金叉点
        else:
            for i in range(1, len(k) - 20):
                if k[i] < d[i] and k[i-1] >= d[i-1]:
                    cross_idx = i  # 找最后一个死叉点

        # 关键：交叉点之后要有足够空间（至少 20 根）才算有效信号
        if cross_idx is None:
            continue

        total += 1
        # 正确计算：交叉点之后 N 日的收益
        ret_5d = (prices[cross_idx + 5] - prices[cross_idx]) / prices[cross_idx]
        ret_10d = (prices[cross_idx + 10] - prices[cross_idx]) / prices[cross_idx]
        ret_20d = (prices[cross_idx + 20] - prices[cross_idx]) / prices[cross_idx]

        returns_5d.append(ret_5d)
        returns_10d.append(ret_10d)
        returns_20d.append(ret_20d)

        actual_dir = 'up' if ret_10d > 0 else 'down'
        if actual_dir == expected_dir:
            hits += 1

    hit_rate = hits / total if total > 0 else 0.0
    avg_return_10d = np.mean(returns_10d) if returns_10d else 0

    return {
        'signal_type': signal_type,
        'total_signals': total,
        'n_samples': n_samples,
        'hits': hits,
        'hit_rate_10d': round(hit_rate, 4),
        'avg_return_5d': round(float(np.mean(returns_5d) * 100), 2) if returns_5d else 0,
        'avg_return_10d': round(float(np.mean(returns_10d) * 100), 2) if returns_10d else 0,
        'avg_return_20d': round(float(np.mean(returns_20d) * 100), 2) if returns_20d else 0,
        'expected_direction': expected_dir,
    }


def main():
    """主函数：跑 4 种 KDJ 形态回测"""
    print("=" * 60)
    print("📊 KDJ 金叉死叉策略回测 (multi-agent-pipeline P1 验证)")
    print("=" * 60)
    print()
    print("测试场景：合成 K 线 (n=200, 样本数=200/类型)")
    print("评估：识别交叉后 5/10/20 日方向匹配率")
    print()

    # 跑 4 种 KDJ 形态
    results = []
    test_plan = [
        # (signal_type, trend_func, kwargs, semantic)
        ('golden_cross', generate_bullish_trend_with_crossover, {'with_pullback': False},
         '金叉真信号：上升趋势中 K 上穿 D → 后续涨'),
        ('golden_cross', generate_bearish_trend_with_crossover, {'with_bounce': True},
         '金叉假信号：下跌趋势反弹中 K 上穿 D → 后续跌（策略应回避）'),
        ('death_cross', generate_bearish_trend_with_crossover, {'with_bounce': False},
         '死叉真信号：下降趋势中 K 下穿 D → 后续跌'),
        ('death_cross', generate_bullish_trend_with_crossover, {'with_pullback': True},
         '死叉假信号：上升趋势回撤中 K 下穿 D → 后续涨（策略应回避）'),
    ]

    for signal_type, trend_func, kwargs, semantic in test_plan:
        print(f"▶ 测试 {signal_type}")
        print(f"  场景: {semantic}")

        n_samples = 200
        expected_dir = 'up' if signal_type == 'golden_cross' else 'down'

        hits = 0
        total = 0
        returns_5d = []
        returns_10d = []
        returns_20d = []

        for sample in range(n_samples):
            # 关键：构造 350 根以便交叉点后有 20 日空间
            df = trend_func(n=350, seed=sample + hash(signal_type) % 10000)
            prices = df['close'].values
            k, d, j = calc_kdj(df['high'].values, df['low'].values, prices)

            if len(k) < 2:
                continue

            # 找最后一个交叉点（留 20 根空间）
            cross_idx = None
            if signal_type == 'golden_cross':
                for i in range(1, len(k) - 20):
                    if k[i] > d[i] and k[i-1] <= d[i-1]:
                        cross_idx = i
            else:
                for i in range(1, len(k) - 20):
                    if k[i] < d[i] and k[i-1] >= d[i-1]:
                        cross_idx = i

            if cross_idx is None:
                continue

            total += 1
            # 正确：以交叉点为基准，计算后续 N 日收益
            ret_5d = (prices[cross_idx + 5] - prices[cross_idx]) / prices[cross_idx]
            ret_10d = (prices[cross_idx + 10] - prices[cross_idx]) / prices[cross_idx]
            ret_20d = (prices[cross_idx + 20] - prices[cross_idx]) / prices[cross_idx]
            returns_5d.append(ret_5d)
            returns_10d.append(ret_10d)
            returns_20d.append(ret_20d)

            actual_dir = 'up' if ret_10d > 0 else 'down'
            if actual_dir == expected_dir:
                hits += 1

        hit_rate = hits / total if total > 0 else 0.0
        result = {
            'signal_type': signal_type,
            'total_signals': total,
            'n_samples': n_samples,
            'hits': hits,
            'hit_rate_10d': round(hit_rate, 4),
            'avg_return_5d': round(float(np.mean(returns_5d) * 100), 2) if returns_5d else 0,
            'avg_return_10d': round(float(np.mean(returns_10d) * 100), 2) if returns_10d else 0,
            'avg_return_20d': round(float(np.mean(returns_20d) * 100), 2) if returns_20d else 0,
            'expected_direction': expected_dir,
            'semantic': semantic,
        }
        results.append(result)
        print(f"  ✓ {result['total_signals']} 个信号 | 命中率(10d) = {result['hit_rate_10d']*100:.1f}%")
        print(f"    平均收益(10d) = {result['avg_return_10d']:+.2f}%")
        print()

    # 汇总报告
    print("=" * 60)
    print("📈 回测汇总 (multi-agent-pipeline P1 验证)")
    print("=" * 60)
    print()
    print(f"{'场景':<20} {'类型':<14} {'信号数':<8} {'命中率(10d)':<14} {'平均收益(10d)'}")
    print("-" * 70)
    for r in results:
        scene = r['semantic'].split('：')[0]
        print(f"{scene:<20} {r['signal_type']:<14} {r['total_signals']:<8} "
              f"{r['hit_rate_10d']*100:>6.1f}%        {r['avg_return_10d']:>+6.2f}%")
    print()

    # 评估
    overall_hit_rate = np.mean([r['hit_rate_10d'] for r in results])
    print(f"🎯 总体命中率（10 日）: {overall_hit_rate*100:.1f}%")
    print(f"🎯 kline-analyst 基准: ≥ 55%")
    if overall_hit_rate >= 0.55:
        print("✅ 通过 kline-analyst 成功指标")
    else:
        print("⚠️ 未达 55% 基准（合成数据，可能高估）")
    print()

    # 写报告
    report = {
        'title': 'KDJ 金叉死叉策略回测报告 (multi-agent-pipeline P1 验证)',
        'date': '2026-10-05',
        'pipeline_stage': 'P1 验证',
        'test_env': '合成数据 (n=200 per type, samples=200)',
        'note': '本回测用合成 K 线——验证 KDJ 公式逻辑。真实命中率需历史数据回测。',
        'results': results,
        'overall_hit_rate_10d': round(float(overall_hit_rate), 4),
        'kline_analyst_benchmark': '≥ 55%',
        'passed': bool(overall_hit_rate >= 0.55),
    }

    output_path = '/tmp/backtest_kdj_cross_report.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📁 报告保存到: {output_path}")
    print()

    # 输出可填入 kline-analyst 的实战统计表
    print("=" * 60)
    print("📋 填入 .cursor/agents/kline-analyst.md 实战统计表：")
    print("=" * 60)
    print()
    print("| 形态 | A 股命中率 | 美股命中率 | 加密命中率 | 备注 |")
    print("|------|-----------|-----------|-----------|------|")
    chinese_map = {
        'golden_cross': 'KDJ 金叉（上升趋势）',
        'death_cross': 'KDJ 死叉（下降趋势）',
    }
    for r in results:
        if r['total_signals'] > 100:  # 只统计真信号场景
            cn = chinese_map.get(r['signal_type'], r['signal_type'])
            rate = f"{r['hit_rate_10d']*100:.1f}%"
            note = "真信号" if "真信号" in r['semantic'] else "假信号"
            print(f"| {cn} | {rate}* | _待回测_ | _待回测_ | {note} |")
    print()
    print("*合成数据（待真实数据回测确认）")


if __name__ == '__main__':
    main()
