# 从 ai-trader 学到的教训（kline-system 必读）

> **来源**: [bobing888/ai-trader](https://github.com/bobing888/ai-trader) 完整复盘
> **日期**: 2026-10-04
> **目的**: 把 ai-trader 的 10 个坑转成 kline-system 的 10 条红线

---

## 🔴 教训 #1：规范不是愿望清单

**ai-trader 现状**：
- `AGENTS.md` 写了 9 条规则
- 但 `SignalAggregator affinity matrix` 只有概念无实现
- 标记 `markers` 接口"已预留但未接入"
- 规范 vs 实现脱节

**kline-system 怎么办**：
- 规范必须**可测试**（每条规则对应可执行的验证方式）
- 没有测试覆盖的规则不算"实现"
- `SPEC.md` 顶部明确 10 条原则 + 量化验收表

---

## 🔴 教训 #2：信号质量是生命线

**ai-trader 现状**：
- 回测命中率 **49.8%**（≈ 随机）
- AUC 0.506（≈ 0.5 的随机基线）
- Brier score 0.2777（信度低）
- **仍被接受为 "baseline"**

**kline-system 怎么办**：
- M2.3 硬性验收：**命中率 > 55%**，否则不上线
- Brier score < 0.25
- outcome tracking 24h 自动校准
- PAVA Isotonic 校准器（ai-trader 复用的 `calibration.py`）

---

## 🟠 教训 #3：数据层先于 AI 层

**ai-trader 现状**：
- 先接了 OKX WebSocket（实时数据流）
- 但 signal aggregator 没实现 → "实时数据进了死胡同"
- 数据进来了但没人用

**kline-system 怎么办**：
- M1 数据层 100% 就绪后，**才能开 M2**
- Redis 缓存必须**实际使用**（ai-trader 配了不用）
- 数据完整率 ≥ 99% 验收

---

## 🟠 教训 #4：TDD 不是银弹

**ai-trader 现状**：
- 40+ pytest 全过
- 但信号质量 49.8% 仍通过所有测试
- 因为测试只测"代码是否跑通"（HTTP 200/类型检查）
- 不测"信号是否有效"

**kline-system 怎么办**：
- 测试必须测**业务指标**（命中率/校准/多指标一致性）
- 不允许只测技术指标
- 业务指标测试用例见 `SPEC.md` 的业务指标验收表

---

## 🟠 教训 #5：复用代码必须写 license 出处

**ai-trader 现状**：
- `LightweightKlineChart.tsx` 有完整实现可参考
- 但 `docs/architecture/w1-summary.md` 提到"借鉴了 5 个 React 项目源码"却没有具体标注

**kline-system 怎么办**：
- `backend/app/analytics/__init__.py` 明确标注：
  - 来源仓库 URL
  - 复用的具体文件
  - 复用的具体函数
  - 注意事项
- 任何后续修改必须更新 header

---

## 🟡 教训 #6：前端骨架屏优先

**ai-trader 现状**：
- `RecommendationsPage` 加载时：空白 → loading spinner → 数据
- 用户感知等待 > 实际等待
- 没有 skeleton loading

**kline-system 怎么办**：
- M3.0 设计系统第一件事：`GlassSkeleton` + `KlineChartSkeleton`
- 所有数据加载场景必须用骨架屏
- 智能预取（hover 150ms）减少实际加载

---

## 🟡 教训 #7：后端数据必须前端可视化

**ai-trader 现状**：
- `analytics/trend.py` 计算了 ADX/MACD/SMA/RSI
- 但前端图表完全没有叠加这些指标
- "数据不展示 = 没有价值"

**kline-system 怎么办**：
- M3.3 验收：**所有后端指标必须前端可见**
- 指标 Panel + 主图叠加双路径
- 测试场景：每个指标都有截图证据

---

## 🟡 教训 #8：FALLBACK 路径必须有降级逻辑

**ai-trader 现状**：
- 无 `DEEPSEEK_API_KEY` 时，Agent 全 FALLBACK
- 但 FALLBACK 后只输出"建议人工 review"
- 用户体验断裂

**kline-system 怎么办**：
- FALLBACK 路径必须有降级逻辑（纯规则引擎兜底）
- 不允许"无 AI 时直接给空白"
- kline-analyst agent 设计时考虑 FALLBACK 路径

---

## 🟡 教训 #9：多市场交互矩阵先于组件实现

**ai-trader 现状**：
- 只支持加密货币（绿涨红跌）→ 配色简单
- kline-system 要支持 A 股（红涨绿跌）+ 美股 + 加密
- 复杂度不是 3x 而是交互矩阵 3×3（颜色 × 数据格式 × 涨跌停逻辑）

**kline-system 怎么办**：
- M3.0 设计系统先实现 **MarketThemeProvider**（多市场主题切换）
- 每个组件必须先考虑多市场情况，再实现单一组件
- 测试场景矩阵：3 市场 × 2 设备类型 = 6 个场景

---

## 🟡 教训 #10：每个 PR 必过 5 道质量门禁

**ai-trader 现状**：
- 规则很多但门禁松
- PR 合入后经常返工

**kline-system 怎么办**：
1. 代码覆盖率 ≥ 80%
2. 类型检查 mypy strict + tsc --noEmit
3. 业务指标测试（不是技术测试）
4. 场景覆盖矩阵 ≥ 3 个用户场景
5. ai-trader 教训自检：勾选 10 条红线，有违反必须 PR 描述解释

---

## 📚 引用

- [完整复盘 Canvas](../canvases/ai-trader-architecture-review.canvas.tsx)
- [完整规范 SPEC.md](../SPEC.md)
- [ai-trader GitHub](https://github.com/bobing888/ai-trader)
