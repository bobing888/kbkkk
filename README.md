# Kbkkk — BTC / ETH K 线趋势分析系统

> 只分析 BTC 和 ETH · 多周期 K 线 + 技术指标 + 信号生成 + 跟单回测

## 只做两件事

- **K 线数据**：BTC / ETH 全周期覆盖（1m / 5m / 15m / 1h / 4h / 1d）
- **趋势分析**：技术指标 + 形态识别 + 买卖信号 + 置信度 + 回测

## 技术栈

| 层级 | 技术 |
|------|------|
| 数据获取 | akshare（A 股）/ yfinance（美股）/ **ccxt（Binance，优先）** |
| 指标计算 | 纯 numpy（ADX / MACD / SMA / RSI / 布林带 / KDJ / OBV / ATR / Hurst）|
| 后端 | Python 3.14 + FastAPI + SQLAlchemy 2.0 + PostgreSQL + Redis |
| 前端 | React 18 + TypeScript + lightweight-charts v5 + Zustand + TanStack Query |
| 回测 | Backtrader |

## 当前进度

| 模块 | 状态 | 说明 |
|------|------|------|
| M1 数据基础设施 | 🟡 进行中 | 数据层代码就绪，pip 依赖安装中 |
| M2 分析引擎 | ⏸️ 未开始 | 目标：信号命中率 > 55% |
| M3 前端可视化 | ⏸️ 未开始 | macOS Sonoma 设计系统 |
| M4 API + 风控 | ⏸️ 未开始 | |
| M5 集成 + 交付 | ⏸️ 未开始 | |

## 快速开始

```bash
cd kbkkk/backend

# 装依赖（M1 进行中，可能需手动装）
pip install -r requirements.txt

# 启动（需 PostgreSQL + Redis）
uvicorn app.main:app --reload --port 8000

# 健康检查
curl http://localhost:8000/api/v1/health
```

### 获取 BTC / ETH 数据

```bash
# BTC 1h K 线（加密市场）
curl "http://localhost:8000/api/v1/kline/BTC/USDT?period=1h&market=crypto"

# ETH 1d K 线
curl "http://localhost:8000/api/v1/kline/ETH/USDT?period=1d&market=crypto"

# AAPL（美股对比参考）
curl "http://localhost:8000/api/v1/kline/AAPL?period=1d&market=us"
```

## 目录结构

```
kbkkk/
├── backend/
│   ├── app/
│   │   ├── analytics/          # ★ 高级指标（ai-trader 复用）
│   │   │   ├── trend.py       # ADX / MACD / SMA / 多指标共振
│   │   │   ├── statistical.py # Hurst 指数 / Shannon 熵 / 分形维数
│   │   │   └── volatility.py  # ATR / 波动率分位数
│   │   ├── services/
│   │   │   ├── data_fetcher.py  # akshare / yfinance / ccxt
│   │   │   ├── indicators.py     # pandas 指标引擎
│   │   │   ├── event_bus.py     # asyncio pub/sub
│   │   │   └── calibration.py   # PAVA Isotonic 校准
│   │   ├── routers/kline.py
│   │   ├── models/             # ORM 5 表
│   │   └── main.py
│   └── tests/
│       ├── test_data_fetcher.py
│       └── test_business_metrics.py  # 业务指标测试
├── frontend/                   # M3 启动
├── docs/
│   ├── lessons-from-ai-trader.md  # ai-trader 教训
│   └── 01-project-spec.md
├── SPEC.md                    # 团队宪法（10 条原则 + 验收标准）
└── README.md
```

## 设计原则（来自 ai-trader 复盘）

| # | 原则 |
|---|------|
| 1 | 数据层 100% 就绪后，才能开分析层 |
| 2 | 后端计算的数据，前端必须可视化 |
| 3 | 每个 milestone 有量化验收标准（命中率 > 55%）|
| 4 | 测试必须测业务指标，不只是 HTTP 200 |
| 5 | design tokens 强制执行 |
| 6 | 同一概念不允许两套实现 |
| 7 | FALLBACK 路径必须有降级逻辑 |
| 8 | 代码前先看 GitHub 调研 |
| 9 | 骨架屏是感知性能核心 |
| 10 | 多市场交互矩阵先于组件实现 |

详细见 [SPEC.md](SPEC.md)。

## 参考项目

- [bobing888/ai-trader](https://github.com/bobing888/ai-trader) — 本项目前身，复盘后谨慎复用其 analytics 模块（MIT/Apache-2.0）

## 许可

仅供研究学习，不构成投资建议。

<!-- kbkkk auto-merge e2e test -->
