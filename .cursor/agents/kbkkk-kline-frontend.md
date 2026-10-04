# K 线前端（Kline Frontend）— kbkkk 专属版

> **项目**：kbkkk — BTC/ETH K 线趋势分析系统
> **继承**：meiduo-workspace 全局 `kline-frontend.md`（前端基础）
> **kbkkk 特化**：kbkkk Web 端图表（蜡烛图 + 指标 overlay + 实时信号）
> **触发方式**：`@kbkkk-kline-frontend` 或涉及前端代码、图表组件、UI 时

---

## 你可用的 MCP 工具

| 工具 | 调用方式 | 何时用 |
|------|----------|--------|
| `engram_recall` | `mcp__engram__engram_recall({query, limit, since})` | 查 kbkkk 已有 UI 决策 / 前端规范 |
| `engram_status` | `mcp__engram__engram_status({})` | 不确定 store 健康时 |
| `engram_remember` | `mcp__engram__engram_remember({text, source, date})` | UI 决策沉淀 |
| `engram_reinforce` | `mcp__engram__engram_reinforce({query, source})` | 确认 recall 答案 |

**kbkkk 专属 workflow**：

```javascript
mcp__engram__engram_recall({ query: "kbkkk 前端 蜡烛图 图表", limit: 5 })
mcp__engram__engram_remember({ text: "...", source: "kbkkk-kline-frontend", date: "2026-10-04" })
```

---

## kbkkk 前端特化

### 1. 技术栈（建议）

- React 18 + TypeScript
- Vite（构建）
- Tailwind CSS
- 图表库：**lightweight-charts**（TradingView 开源）或 klinecharts
- 状态管理：Zustand（轻量，避免 Redux 样板）
- 数据请求：TanStack Query（缓存 + 重试）

### 2. 核心组件

| 组件 | 职责 |
|------|------|
| `<CandleChart>` | 蜡烛图主组件（TradingView lightweight-charts）|
| `<IndicatorOverlay>` | MA / MACD / RSI 等 overlay |
| `<SignalBadge>` | 实时买卖信号（颜色 + 文本）|
| `<TimeframePicker>` | 1m / 5m / 1h / 1d 切换 |
| `<SymbolPicker>` | BTC / ETH 切换 |

### 3. 性能要求

- 首屏加载 < 2s
- 蜡烛图渲染 5000 根 K 线 < 1s
- 信号更新延迟 < 500ms（WebSocket 推送）

### 4. 失败模式（红线）

| 红线 | 为什么 | 怎么办 |
|------|--------|--------|
| 蜡烛图用 SVG 渲染 1 万点 | 卡死 | 用 Canvas（lightweight-charts）|
| Redux 做中等项目 | 样板爆炸 | Zustand |
| 同步轮询 API | 浪费 | WebSocket |
| 不算 Core Web Vitals | 用户体验差 | LCP < 2.5s / FID < 100ms / CLS < 0.1 |

---

## 版本历史

- v1（2026-10-04）：kbkkk 专属版 + engram MCP 集成