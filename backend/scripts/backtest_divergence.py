"""
backtest_divergence.py — 4 类量价背离回测
=========================================

对应 kline-analyst v2.1 Phase 3.5 (量价背离识别 4 类型判定)

原理：
  - 4 类背离：普通顶/底（趋势反转）vs 隐性顶/底（趋势延续）
  - 验证：识别某类型背离后，未来 N 日的方向是否如预期
  - 数据：合成 4 类形态（每类 200 个样本）—— 因为网络拉不到真实数据
  - 评估：命中率（信号方向 / 实际方向匹配率）

合成数据规则（按 Steve Nison 量价背离经典体系）：
  1. 普通顶背离 (Regular Bearish)：价格 HH + RSI LH → 后续 10 日应下跌
  2. 普通底背离 (Regular Bullish)：价格 LL + RSI HL → 后续 10 日应上涨
  3. 隐性顶背离 (Hidden Bearish)：价格 LH + RSI HH → 后续 10 日继续下跌
  4. 隐性底背离 (Hidden Bullish)：价格 HL + RSI LL → 后续 10 日继续上涨

评估：
  - 命中率 = 信号方向匹配实际方向的比例
  - 目标：≥ 55%（kline-analyst 成功指标基准）

用法：
  python3 scripts/backtest_divergence.py
  # 输出：4 类背离的命中率 + 报告
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import List
import json


@dataclass
class DivergenceSignal:
    """背离信号"""
    type: str  # 'regular_bearish' / 'regular_bullish' / 'hidden_bearish' / 'hidden_bullish'
    confidence: float  # 0-1
    entry_price: float
    expected_direction: str  # 'down' / 'up'
    actual_return_5d: float = 0.0
    actual_return_10d: float = 0.0
    actual_return_20d: float = 0.0
    hit: bool = False  # 实际方向匹配预期方向


def detect_regular_bearish(prices: np.ndarray, rsi: np.ndarray) -> bool:
    """
    普通顶背离：价格 HH + RSI LH
    即：当前价格 > 前 N 日最高，且当前 RSI < 前 N 日最高
    """
    if len(prices) < 20:
        return False
    # 看最后 10 个 vs 之前 10 个
    price_now = prices[-1]
    price_prev_high = prices[-20:-10].max()
    rsi_now = rsi[-1]
    rsi_prev_high = rsi[-20:-10].max()

    return price_now > price_prev_high and rsi_now < rsi_prev_high


def detect_regular_bullish(prices: np.ndarray, rsi: np.ndarray) -> bool:
    """
    普通底背离：价格 LL + RSI HL
    """
    if len(prices) < 20:
        return False
    price_now = prices[-1]
    price_prev_low = prices[-20:-10].min()
    rsi_now = rsi[-1]
    rsi_prev_low = rsi[-20:-10].min()

    return price_now < price_prev_low and rsi_now > rsi_prev_low


def detect_hidden_bearish(prices: np.ndarray, rsi: np.ndarray) -> bool:
    """
    隐性顶背离：价格 LH + RSI HH
    即：当前价格 < 前段最高（回调中），但 RSI > 前段最高（动能仍在）
    """
    if len(prices) < 20:
        return False
    price_now = prices[-1]
    price_prev_high = prices[-20:-10].max()
    rsi_now = rsi[-1]
    rsi_prev_high = rsi[-20:-10].max()

    return price_now < price_prev_high and rsi_now > rsi_prev_high


def detect_hidden_bullish(prices: np.ndarray, rsi: np.ndarray) -> bool:
    """
    隐性底背离：价格 HL + RSI LL
    即：当前价格 > 前段最低（回升中），但 RSI < 前段最低（动能尚未恢复）
    """
    if len(prices) < 20:
        return False
    price_now = prices[-1]
    price_prev_low = prices[-20:-10].min()
    rsi_now = rsi[-1]
    rsi_prev_low = rsi[-20:-10].min()

    return price_now > price_prev_low and rsi_now < rsi_prev_low


def calc_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """计算 RSI"""
    delta = np.diff(prices, prepend=prices[0])
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(period, min_periods=1).mean().values
    avg_loss = pd.Series(loss).rolling(period, min_periods=1).mean().values
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def generate_bullish_trend(n: int = 200, seed: int = 42, with_pullback: bool = False) -> pd.DataFrame:
    """
    生成上升趋势 K 线（用于普通底/隐性底背离测试）

    参数:
      with_pullback: True = 末段回撤（用于隐性底/普通底测试）
                    False = 单纯上升
    """
    np.random.seed(seed)
    # 基础上升 + 波动
    trend = np.linspace(100, 200, n)
    noise = np.random.normal(0, 3, n)
    close = trend + noise
    # 量能：上升期 + 末段缩量
    volume = np.random.normal(1000, 200, n)
    volume[150:] *= 0.6  # 末段缩量（构造底背离）
    if with_pullback:
        close[180:] *= 0.95  # 末段小回撤（构造底背离形态）
    return pd.DataFrame({'close': close, 'volume': volume})


def generate_bearish_trend(n: int = 200, seed: int = 42, with_bounce: bool = False) -> pd.DataFrame:
    """
    生成下降趋势 K 线（用于普通顶/隐性顶背离测试）

    参数:
      with_bounce: True = 末段反弹（用于隐性顶/普通顶测试）
    """
    np.random.seed(seed)
    trend = np.linspace(200, 100, n)
    noise = np.random.normal(0, 3, n)
    close = trend + noise
    volume = np.random.normal(1000, 200, n)
    volume[150:] *= 0.6
    if with_bounce:
        close[180:] *= 1.05  # 末段反弹（构造顶背离形态）
    return pd.DataFrame({'close': close, 'volume': volume})


def backtest_divergence_type(
    div_type: str,
    trend_func,
    n_samples: int = 200,
    forward_days: int = 10,
) -> dict:
    """
    回测 1 类背离的命中率

    参数:
      div_type: 'regular_bearish' / 'regular_bullish' / 'hidden_bearish' / 'hidden_bullish'
      trend_func: 趋势生成函数（generate_bullish_trend / generate_bearish_trend）
      n_samples: 样本数
      forward_days: 前向天数

    返回:
      dict: 命中率统计
    """
    detectors = {
        'regular_bearish': detect_regular_bearish,
        'regular_bullish': detect_regular_bullish,
        'hidden_bearish': detect_hidden_bearish,
        'hidden_bullish': detect_hidden_bullish,
    }
    detector = detectors[div_type]

    # 预期方向
    is_bullish = div_type in ('regular_bullish', 'hidden_bullish')
    expected_dir = 'up' if is_bullish else 'down'

    hits = 0
    total = 0
    returns_5d = []
    returns_10d = []
    returns_20d = []

    for sample in range(n_samples):
        df = trend_func(n=200, seed=sample + hash(div_type) % 10000)
        prices = df['close'].values
        rsi = calc_rsi(prices, period=14)

        if detector(prices, rsi):
            total += 1
            # 计算 forward N 日收益
            ret_5d = (prices[-1 + 5] - prices[-1]) / prices[-1] if len(prices) >= 11 else 0
            ret_10d = (prices[-1 + 10] - prices[-1]) / prices[-1] if len(prices) >= 11 else 0
            ret_20d = (prices[-1 + 20] - prices[-1]) / prices[-1] if len(prices) >= 21 else 0

            returns_5d.append(ret_5d)
            returns_10d.append(ret_10d)
            returns_20d.append(ret_20d)

            # 方向匹配
            actual_dir = 'up' if ret_10d > 0 else 'down'
            if actual_dir == expected_dir:
                hits += 1

    hit_rate = hits / total if total > 0 else 0.0
    avg_return_10d = np.mean(returns_10d) if returns_10d else 0

    return {
        'div_type': div_type,
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
    """主函数：跑 4 类背离回测"""
    print("=" * 60)
    print("📊 4 类量价背离回测 (kline-analyst v2.1 Phase 3.5)")
    print("=" * 60)
    print()
    print("测试场景：合成 K 线 (n=200, 样本数=200/类)")
    print("评估：识别背离后 5/10/20 日方向匹配率")
    print()

    # 跑 4 类
    results = []
    test_plan = [
        # (div_type, trend_func, kwargs, expected_dir, semantic)
        # 普通顶背离：上升趋势末段反弹 → 实际应下跌（反转）
        ('regular_bearish', generate_bullish_trend, {'with_pullback': False}, 'down', '反转：上升趋势中价格 HH + RSI LH → 后续跌'),
        # 普通底背离：下降趋势末段回撤 → 实际应上涨（反转）
        ('regular_bullish', generate_bearish_trend, {'with_bounce': False}, 'up', '反转：下降趋势中价格 LL + RSI HL → 后续涨'),
        # 隐性顶背离：下降趋势中反弹 → 实际应继续下跌（趋势延续）
        ('hidden_bearish', generate_bearish_trend, {'with_bounce': True}, 'down', '趋势延续：下降趋势中价格 LH + RSI HH → 继续跌'),
        # 隐性底背离：上升趋势中回撤 → 实际应继续上涨（趋势延续）
        ('hidden_bullish', generate_bullish_trend, {'with_pullback': True}, 'up', '趋势延续：上升趋势中价格 HL + RSI LL → 继续涨'),
    ]

    for div_type, trend_func, kwargs, expected_dir, semantic in test_plan:
        print(f"▶ 测试 {div_type}")
        print(f"  场景: {semantic}")

        # 包装 trend_func
        def wrap(seed):
            return trend_func(n=200, seed=seed, **kwargs)

        # 直接调用
        n_samples = 200
        detector_map = {
            'regular_bearish': detect_regular_bearish,
            'regular_bullish': detect_regular_bullish,
            'hidden_bearish': detect_hidden_bearish,
            'hidden_bullish': detect_hidden_bullish,
        }
        detector = detector_map[div_type]

        hits = 0
        total = 0
        returns_5d = []
        returns_10d = []
        returns_20d = []

        for sample in range(n_samples):
            df = wrap(sample + hash(div_type) % 10000)
            prices = df['close'].values
            rsi = calc_rsi(prices, period=14)

            if detector(prices, rsi):
                total += 1
                ret_5d = (prices[-1 + 5] - prices[-1]) / prices[-1] if len(prices) >= 11 else 0
                ret_10d = (prices[-1 + 10] - prices[-1]) / prices[-1] if len(prices) >= 11 else 0
                ret_20d = (prices[-1 + 20] - prices[-1]) / prices[-1] if len(prices) >= 21 else 0
                returns_5d.append(ret_5d)
                returns_10d.append(ret_10d)
                returns_20d.append(ret_20d)

                actual_dir = 'up' if ret_10d > 0 else 'down'
                if actual_dir == expected_dir:
                    hits += 1

        hit_rate = hits / total if total > 0 else 0.0
        result = {
            'div_type': div_type,
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
    print("📈 回测汇总 (kline-analyst v2.1 实战统计)")
    print("=" * 60)
    print()
    print(f"{'类型':<20} {'信号数':<8} {'命中率(10d)':<14} {'平均收益(10d)'}")
    print("-" * 60)
    for r in results:
        print(f"{r['div_type']:<20} {r['total_signals']:<8} {r['hit_rate_10d']*100:>6.1f}%        {r['avg_return_10d']:>+6.2f}%")
    print()

    # 评估是否达到 kline-analyst 成功指标 ≥ 55%
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
        'title': '4 类量价背离回测报告 (kline-analyst v2.1 Phase 3.5)',
        'date': '2026-10-04',
        'test_env': '合成数据 (n=200 per type, samples=200)',
        'note': '本回测用合成 K 线——因网络拉不到真实数据。回测目的是验证公式逻辑，真实命中率需历史数据回测。',
        'results': results,
        'overall_hit_rate_10d': round(float(overall_hit_rate), 4),
        'kline_analyst_benchmark': '≥ 55%',
        'passed': bool(overall_hit_rate >= 0.55),
    }

    output_path = '/tmp/backtest_divergence_report.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📁 报告保存到: {output_path}")
    print()

    # 输出可填入 kline-analyst 的实战统计表
    print("=" * 60)
    print("📋 填入 .cursor/agents/kline-analyst.md 实战统计表：")
    print("=" * 60)
    print()
    print("| 背离类型 | A 股命中率 | 美股命中率 | 加密命中率 | 备注 |")
    print("|---------|-----------|-----------|-----------|------|")
    chinese_map = {
        'regular_bearish': '普通顶背离',
        'regular_bullish': '普通底背离',
        'hidden_bearish': '隐性顶背离',
        'hidden_bullish': '隐性底背离',
    }
    for r in results:
        cn = chinese_map[r['div_type']]
        rate = f"{r['hit_rate_10d']*100:.1f}%"
        note = "反转" if "regular" in r['div_type'] else "趋势延续"
        print(f"| {cn} | {rate}* | _待回测_ | _待回测_ | {note} |")
    print()
    print("*合成数据（待真实数据回测确认）")


if __name__ == '__main__':
    main()
