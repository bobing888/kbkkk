# K 线趋势分析系统 - 项目规格说明书

**版本**：v1.0
**创建日期**：2026-10-04
**PM**：kline-pm
**最后更新**：2026-10-04

---

## 1. 项目目标

构建一个专业的 K 线趋势分析系统，覆盖 A 股 / 美股 / 加密货币，提供：
- **量化分析**：技术指标计算 + 形态识别 + 缠论 + 波浪理论
- **可视化**：专业级 K 线图表（蜡烛图 + 指标叠加 + 买卖标注）
- **回测验证**：所有策略必须经过跨市场回测
- **实时信号**：信号预警 + 风控建议

## 2. 核心用户故事

### US-001：K线分析
**作为** 交易员，**我希望** 输入股票代码看到专业的 K 线分析报告，**以便** 快速判断买卖点。

**验收标准**：
- [ ] 输入股票代码 → 显示 K 线图 + 技术指标
- [ ] 显示买卖点建议（含止损/止盈/置信度）
- [ ] 支持多周期切换（日/60分/15分）
- [ ] 1 万根 K 线滚动 ≥ 50fps
- [ ] WCAG 2.1 AA 无障碍

### US-002：回测验证
**作为** 量化研究员，**我希望** 用历史数据验证策略，**以便** 评估策略可靠性。

**验收标准**：
- [ ] 选择策略 + 标的 + 时间范围 → 跑回测
- [ ] 输出关键指标（年化收益/最大回撤/夏普/胜率/盈亏比）
- [ ] 生成可视化报告（HTML/PDF）
- [ ] 跨市场对比（A 股 / 美股 / 加密）

### US-003：信号预警
**作为** 交易员，**我希望** 实时收到交易信号，**以便** 抓住交易机会。

**验收标准**：
- [ ] 实时监控持仓标的
- [ ] 信号触发时推送（WebSocket / 邮件 / App）
- [ ] 信号包含：方向、强度、止损、止盈

## 3. 智能体团队

| # | 智能体 | 角色 | 文件 |
|---|--------|------|------|
| 1 | kline-analyst | K 线分析师 | `.cursor/agents/kline-analyst.md` |
| 2 | kline-frontend | 前端工程师 | `.cursor/agents/kline-frontend.md` |
| 3 | kline-backend | 后端工程师 | `.cursor/agents/kline-backend.md` |
| 4 | kline-pm | 项目经理 | `.cursor/agents/kline-pm.md` |
| 5 | kline-learner | 学习规划师 | `.cursor/agents/kline-learner.md` |
| 6 | kline-orchestrator | 编排者 | `.cursor/agents/kline-orchestrator.md` |

## 4. 技术栈

### 前端
- React 18 + TypeScript + Vite
- lightweight-charts（TradingView 开源，WebGL 加速）
- Zustand（状态管理）
- Tailwind CSS（样式）
- Workbox（PWA 离线）

### 后端
- Python 3.11+ + FastAPI
- pandas + pandas_ta（指标计算）
- akshare（A 股） / yfinance（美股） / ccxt（加密）
- Backtrader + quantstats（回测）
- PostgreSQL（时序数据）+ Redis（实时缓存）

### 部署
- Docker + Docker Compose
- GitHub Actions（CI/CD）
- Prometheus + Grafana（监控）

## 5. 里程碑规划

| 里程碑 | 周期 | 主题 | 主要交付物 |
|--------|------|------|----------|
| M1 | W1-W2 | 数据基础设施 | data_fetcher + schema + tests |
| M2 | W3-W5 | 分析引擎 | indicators + signal_generator + backtest |
| M3 | W4-W7 | 前端可视化 | K 线看板 + 指标叠加 + PWA |
| M4 | W6-W8 | API + 风控 | FastAPI + risk_engine + monitoring |
| M5 | W9-W10 | 集成 + 交付 | 全链路联调 + 部署 + 文档 |

## 6. 质量门禁

| 项 | 目标值 |
|----|-------|
| 代码覆盖率 | 核心模块 ≥ 80%，其他 ≥ 60% |
| API 响应 p95 | < 200ms |
| K 线滚动 FPS | ≥ 50 (1 万根 K 线) |
| Lighthouse 性能 | ≥ 90 |
| 系统可用性 | > 99.9% |

## 7. 风险评估

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| akshare 数据延迟/缺失 | 中 | 高 | 引入 ccxt 备用 |
| akshare 接口变更 | 中 | 中 | 统一封装层 + 监控 |
| 指标过拟合 | 高 | 高 | 跨市场 + 样本外测试 |
| A 股特殊规则处理错误 | 中 | 高 | 充分单元测试 + 实盘小资金验证 |
