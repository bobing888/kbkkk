# K 线趋势分析系统 - 任务列表

**PM**：kline-pm
**创建日期**：2026-10-04
**最后更新**：2026-10-04（M3 重构：macOS Sonoma 设计系统 + 智能预取 + 微交互）

---

## 里程碑 1：数据基础设施（M1 · 第 1-2 周）🟡 进行中

### 1.1 数据获取层
- [ ] 1.1.1 A 股数据获取（akshare 封装） `[负责人: kline-backend] [4h] [交付物: backend/app/services/data_fetcher.py]`
- [ ] 1.1.2 美股数据获取（yfinance 封装） `[负责人: kline-backend] [4h] [交付物: 同上]`
- [ ] 1.1.3 加密货币数据获取（ccxt 封装） `[负责人: kline-backend] [4h] [交付物: 同上]`
- [ ] 1.1.4 A 股数据质量处理（复权/缺失/涨跌停标记） `[负责人: kline-backend] [4h] [交付物: data_cleaner.py]`

### 1.2 数据存储层
- [ ] 1.2.1 PostgreSQL schema 设计（K线/指标/信号/订单表） `[负责人: kline-backend] [6h] [交付物: backend/app/models/schema.sql]`
- [ ] 1.2.2 数据库连接管理（SQLAlchemy + asyncpg） `[负责人: kline-backend] [4h] [交付物: db.py]`
- [ ] 1.2.3 Redis 缓存策略（实时行情 + 热数据） `[负责人: kline-backend] [4h] [交付物: cache.py]`

### 1.3 测试 + 集成
- [ ] 1.3.1 单元测试（数据获取层 ≥ 80% 覆盖率） `[负责人: kline-backend] [4h] [交付物: tests/test_data_fetcher.py]`
- [ ] 1.3.2 集成测试（数据管道端到端） `[负责人: kline-backend] [4h] [交付物: tests/test_data_pipeline.py]`
- [ ] 1.3.3 数据库迁移脚本（Alembic） `[负责人: kline-backend] [3h] [交付物: alembic/]`

---

## 里程碑 2：分析引擎（M2 · 第 3-5 周）⏸️ 未开始

### 2.1 指标计算
- [ ] 2.1.1 MA / EMA 均线
- [ ] 2.1.2 MACD 异同移动平均
- [ ] 2.1.3 RSI 相对强弱指数
- [ ] 2.1.4 布林带 Bollinger Bands
- [ ] 2.1.5 KDJ 随机指标
- [ ] 2.1.6 OBV / MFI 量能指标

### 2.2 形态识别
- [ ] 2.2.1 单 K 形态（10 种）
- [ ] 2.2.2 组合 K 形态（9 种）
- [ ] 2.2.3 缠论中枢 + 笔线段
- [ ] 2.2.4 波浪理论（5 浪驱动 + ABC 修正）

### 2.3 信号生成
- [ ] 2.3.1 多指标共振算法
- [ ] 2.3.2 形态 + 指标组合信号
- [ ] 2.3.3 信号置信度评分

### 2.4 回测系统
- [ ] 2.4.1 Backtrader 集成
- [ ] 2.4.2 A 股特殊规则（涨跌停/T+1）
- [ ] 2.4.3 回测报告生成（quantstats）
- [ ] 2.4.4 跨市场对比分析

---

## 里程碑 3：前端可视化（M3 · 第 4-7 周）⏸️ 未开始

> **设计原则**：毛玻璃 + macOS Sonoma + Spring 物理 + 智能预取（高端大气、体验至上）
> **技术栈**：React 18 + TypeScript + lightweight-charts + Radix UI + Tailwind + Framer Motion + Zustand + React Query

### 3.0 设计系统搭建（0.5 天）★ 新增
- [ ] 3.0.1 macOS Sonoma Design Tokens（颜色 / 圆角 / 间距 / 字号 / 模糊 / spring） `[负责人: kline-frontend] [2h] [交付物: src/styles/tokens.ts]`
- [ ] 3.0.2 Tailwind 配置 + CSS Variables + 暗色背景 + 微噪点 `[负责人: kline-frontend] [1h] [交付物: tailwind.config.ts + globals.css]`
- [ ] 3.0.3 SF Pro Display 字体集成（开源替代） `[负责人: kline-frontend] [0.5h] [交付物: src/styles/fonts.ts]`
- [ ] 3.0.4 自建 ui/ 玻璃组件库（GlassCard / GlassButton / GlassModal / GlassSkeleton / GlassTabs / GlassSegmented） `[负责人: kline-frontend] [4h] [交付物: src/components/ui/*]`
- [ ] 3.0.5 统一动画 variants（fadeInUp / staggerContainer / modalPop / slideInRight） `[负责人: kline-frontend] [1h] [交付物: src/styles/animations.ts]`

### 3.1 项目搭建 + 路由（1 天）
- [ ] 3.1.1 Vite + React 18 + TypeScript 初始化
- [ ] 3.1.2 lightweight-charts + Radix + Framer Motion + Tailwind 安装配置
- [ ] 3.1.3 TanStack Router + 路由级懒加载（React.lazy + Suspense）
- [ ] 3.1.4 PWA 配置（vite-plugin-pwa + manifest + service worker）
- [ ] 3.1.5 状态管理（Zustand + React Query 5）

### 3.2 K 线主图组件（3 天）
- [ ] 3.2.1 lightweight-charts 集成（WebGL，1 万根 K 线 60fps）
- [ ] 3.2.2 蜡烛图 + 成交量叠加（多市场颜色：A 股红涨绿跌 / 美股绿涨红跌）
- [ ] 3.2.3 缩放 / 滚动 / 十字光标 / 工具提示（Tooltip）
- [ ] 3.2.4 包入 GlassCard 容器 + 入场 spring 动画
- [ ] 3.2.5 **KlineChartSkeleton 骨架屏**（仿真蜡烛轮廓 + shimmer 动画） `[负责人: kline-frontend] [3h]`
- [ ] 3.2.6 1 万根 K 线性能测试（FPS ≥ 50）

### 3.3 指标叠加（2 天）
- [ ] 3.3.1 MA / EMA / MACD / RSI / 布林带 / KDJ / OBV 独立 Panel（毛玻璃卡片）
- [ ] 3.3.2 指标开关控制（GlassSegmented 多选）
- [ ] 3.3.3 指标参数可调（周期、超买超卖阈值，GlassPopover 弹出）
- [ ] 3.3.4 Panel 列表入场 stagger 动画（依次 50ms）

### 3.4 买卖信号标注（1 天）
- [ ] 3.4.1 后端信号数据接入（WebSocket 实时推送）
- [ ] 3.4.2 箭头 + 浮动标签（spring 弹出动画，0.96 → 1.0 scale）
- [ ] 3.4.3 点击信号查看详情（GlassModal，弹窗 scale+fade 入场）
- [ ] 3.4.4 A 股特殊标记（涨跌停 / 复权 / ST / 停牌日）

### 3.5 多周期切换 + 共享元素动画（1 天）★ 升级
- [ ] 3.5.1 周期选择器（GlassSegmented：1分 / 5分 / 15分 / 60分 / 日 / 周 / 月）
- [ ] 3.5.2 数据重新加载（React Query 缓存 1min staleTime）
- [ ] 3.5.3 **layoutId 共享元素动画**：周期切换时图表 smooth 过渡（Framer Motion）
- [ ] 3.5.4 当前周期高亮（spring 指示器滑动）

### 3.6 ⌘K 命令面板 + 智能预取（1 天）★ 升级
- [ ] 3.6.1 CommandPalette 全局快捷键（⌘K / Ctrl+K） `[负责人: kline-frontend] [3h]`
- [ ] 3.6.2 标的搜索 + 跳转（radix Dialog + Framer Motion scale 弹出）
- [ ] 3.6.3 **usePrefetchSymbol hook**（hover 标的卡片 150ms 防抖预取） `[负责人: kline-frontend] [2h]`
- [ ] 3.6.4 路由级 code splitting（Suspense fallback 用 GlassSkeleton）

### 3.7 响应式 + PWA（1 天）
- [ ] 3.7.1 移动端适配（断点 < 768 / 768-1024 / > 1024）
- [ ] 3.7.2 PWA manifest + service worker（Workbox）
- [ ] 3.7.3 离线模式测试（飞机模式复盘历史 K 线）
- [ ] 3.7.4 顶部 / 底部安全区适配（iPhone notch）

### 3.8 性能优化 + Lighthouse CI（持续）
- [ ] 3.8.1 Lighthouse 跑分 ≥ 90（性能 + 无障碍）
- [ ] 3.8.2 Web Vitals 监控（LCP < 2.5s / FID < 100ms / CLS < 0.1）
- [ ] 3.8.3 Spring 动画 GPU 加速（transform + opacity，避免 `width/height` 动画）
- [ ] 3.8.4 React DevTools Profiler 性能瓶颈分析
- [ ] 3.8.5 组件懒加载（Heavy 组件：`React.lazy` + 错误边界）

### 3.9 设计系统 QA（与 PM 联合）
- [ ] 3.9.1 毛玻璃效果审查（所有浮层 100% 应用 backdrop-filter）
- [ ] 3.9.2 Spring 物理审查（100% 交互用 spring，禁用 linear / ease）
- [ ] 3.9.3 微交互覆盖审查（hover / focus / active 全覆盖）
- [ ] 3.9.4 暗色模式审查（无白色反光，100% 暗色）
- [ ] 3.9.5 骨架屏覆盖审查（所有数据加载场景）
- [ ] 3.9.6 智能预取审查（hover 即预取，150ms 防抖）
- [ ] 3.9.7 Lighthouse 性能 ≥ 90 / WCAG 2.1 AA 无障碍

---

## 里程碑 4：API + 风控（M4 · 第 6-8 周）⏸️ 未开始

### 4.1 风控引擎
- [ ] 4.1.1 仓位控制（单股 ≤ 30% / 总仓 ≤ 70%）
- [ ] 4.1.2 止损止盈（ATR / 支撑位 / 固定比例）
- [ ] 4.1.3 盈亏比检查（≥ 2:1）

### 4.2 FastAPI 接口
- [ ] 4.2.1 REST API（K线 / 信号 / 回测）
- [ ] 4.2.2 WebSocket 实时推送
- [ ] 4.2.3 接口版本控制（v1/v2）
- [ ] 4.2.4 接口文档（自动生成）

### 4.3 监控告警
- [ ] 4.3.1 Prometheus 指标采集
- [ ] 4.3.2 Grafana 仪表盘
- [ ] 4.3.3 告警规则（数据延迟 / API 错误率）

---

## 里程碑 5：集成 + 交付（M5 · 第 9-10 周）⏸️ 未开始

### 5.1 集成测试
- [ ] 5.1.1 前后端联调
- [ ] 5.1.2 A 股数据验证（茅台/平安/沪深300）
- [ ] 5.1.3 全链路回测报告

### 5.2 部署
- [ ] 5.2.1 Docker 容器化
- [ ] 5.2.2 Docker Compose 编排
- [ ] 5.2.3 GitHub Actions CI/CD
- [ ] 5.2.4 生产环境部署

### 5.3 文档 + 培训
- [ ] 5.3.1 API 文档
- [ ] 5.3.2 部署文档
- [ ] 5.3.3 用户手册
- [ ] 5.3.4 演示视频

---

## 进度概览

| 里程碑 | 任务数 | 已完成 | 进度 |
|--------|--------|--------|------|
| M1 数据基础设施 | 10 | 0 | 🟡 0% |
| M2 分析引擎 | 17 | 0 | ⏸️ 0% |
| M3 前端可视化 | 15 | 0 | ⏸️ 0% |
| M4 API + 风控 | 10 | 0 | ⏸️ 0% |
| M5 集成 + 交付 | 11 | 0 | ⏸️ 0% |
| **合计** | **63** | **0** | **0%** |

---

## 当前 Sprint：Sprint 1 (M1 · W1-W2)

**Sprint 目标**：完成数据基础设施（akshare/yfinance/ccxt 封装 + PostgreSQL schema + Redis 缓存 + 单元测试）

**已完成**：0 / 10
**进行中**：0
**阻塞**：0
