# M3 前端可视化 实施计划（V2 返工版 · 基于 SPEC v2.0）

> **创建日期**：2026-10-06
> **设计依据**：[SPEC.md v2.0](../SPEC.md) §M3（line 122-138）— **唯一权威源**
> **范围**：M3 = 4 周前端可视化（9 个子模块：3.0-3.8）
> **执行模式**：SDD（Subagent-Driven Development），3.0+3.1 → 3.2-3.6 → 3.7-3.8 串行
> **关键约束**：
> - **V2 宪法**：本 plan 是 SPEC v2.0 §M3 的实施细化，**不再基于 m3-frontend-pages.md**（v1 时代设计草案）
> - **metrics-first**（你的指令）：业务指标先行，5 个 B 指标不通过即返工
> - **V2 教训硬整合**：8 条 V2 返工教训 → 11 条强制规则
> - **BTC/ETH only**：所有 UI 文案 / 默认值 / 标的列表必须聚焦 BTC + ETH
> - **TDD 铁律**：没有失败测试不写生产代码
> - **不阻塞 main**：所有改动走 feature branch + auto-merge
> - **不破坏基线**：开工前 336 后端 + 6 前端 = **342 passed**（V2 落地后 baseline）

---

## ⚠️ 返工背景

**v1 时代 m3-frontend-pages.md（ac9cdad）问题**：
- 假设 `market: Literal['cn', 'us', 'crypto']` 3 选一（**与 V2 SPEC 冲突**）
- 设计 7 页 + 5 router（**V2 SPEC 砍掉了 7 页概念**，M3 范围 4 周前端可视化）
- 没有 macOS Sonoma 设计系统（**V2 SPEC §3.0 强制要求**）
- 没有 WebSocket 实时信号标注（**V2 SPEC §3.4 强制要求**）

**V2 返工核心**：基于 `SPEC.md v2.0`（v2.0 团队宪法，line 1）重写 M3 plan，**作废 m3-frontend-pages.md**。

**V2 落地 commit 已就位**（`8eca690`）：cn/us provider 已砍，默认 market=crypto，main.py description 改 v2 文案。
**V2 conftest 修复已就位**（`e0bd578`）：v2 contract 测试 7/7 通过。

---

## 验收门禁（metrics-first · V2 SPEC 量化）

> **来源**：SPEC v2.0 §M3 验收表（line 128-138）+ 你的指令（"metrics-first 业务指标先行"）
> **原则**：**业务指标先行于代码**，每个任务必须有可量化验收数字

### 🔴 业务指标门禁（V2 SPEC 量化标准 · 必测，不通过即返工）

| # | 指标 | 目标值 | SPEC 来源 | 测量脚本 |
|---|---|---|---|---|
| **B1** | 7 页首次内容渲染 | **< 2.0s** (p95) | V2 §10 性能原则 | `scripts/verify-b1-page-load.py`（Playwright）|
| **B2** | signal_batch 端到端延迟 | **< 500ms** (p95) | V2 §10 Brier 实时性 | `scripts/verify-b2-signal-latency.py`（httpx async）|
| **B3** | K 线主图滚动 FPS | **≥ 50 FPS**（1 万根 K 线）| **V2 §3.2 强制** | `scripts/verify-b3-kline-fps.py`（Playwright performance API）|
| **B4** | Lighthouse 性能 | **≥ 90** | **V2 §3.8 强制** | `scripts/verify-b4-lighthouse.py`（lighthouse CLI）|
| **B5** | Lighthouse 无障碍 | **≥ 95** | **V2 §3.8 强制** | 同 B4 |
| **B6** | LCP (Largest Contentful Paint) | **< 2.5s** | **V2 §3.8 强制** | 同 B4 |
| **B7** | AI-Trader 教训自检 | **10/10 勾选** | V2 §10 原则 | `scripts/verify-b5-ai-trader-lessons.sh` |

### 🟡 工程指标门禁（V2 SPEC §10 质量门禁）

| 指标 | 当前 baseline | M3 目标 | 说明 |
|---|---|---|---|
| 后端测试通过 | 336 passed | **340+ passed** | + 4+ 新测试（M3 配套 mock）|
| 前端测试通过 | 6 passed | **18+ passed** | + 12 新测试（路由 + 组件 + Playwright）|
| 前端 typecheck | 0 错 | **0 错** | tsc --noEmit 严格 |
| 前端 npm build | — | **必须成功** | 0 警告 |
| 代码覆盖率 | — | **业务模块 ≥ 80%** | V2 §10 #1 强制 |
| 类型检查 | — | **mypy strict + tsc --noEmit** | V2 §10 #2 强制 |

### 🟠 V2 重设计教训 → M3 强制规则（不遵守即返工）

> **来源**：`docs/SPEC-v2-round1-completion-report.md` §7 + `docs/lessons-from-ai-trader.md`

| 教训 | 数字证据 | M3 强制动作 |
|---|---|---|
| **校正节省 50%** | V2 校正发现 2/8 Arch 误判 → 省 2 PR | M3 每个 subagent 开工前 **必读 SPEC.md v2 §M3 + 6 个相关文件** |
| **风险排序 ≠ 工作量** | V2 PR-2 风险最高先做 → 早暴露 hidden bug | M3 任务顺序：**3.0 设计系统 → 3.1 路由骨架 → 3.2 K线主图 → 3.3 指标叠加 → 3.4 信号标注 → 3.5 共享元素 → 3.6 智能预取 → 3.7 响应式 → 3.8 Lighthouse**（依赖链驱动，V2 §M3 子模块顺序） |
| **架构边界自检** | V2 §10 #6 新增：模块导入方向 | M3 前端代码组织按 V2 §M3.0 设计系统（macOS Sonoma tokens）|
| **AsyncClient 绕开 main app** | V2 .env 与 pydantic v2 冲突 | M3 配套 backend mock 用 `httpx.AsyncClient + ASGITransport` |
| **commit 立即 push** | V2: PR-3 被 `reset --hard origin/main` 覆盖 → reflog 救回 | M3 subagent **每 commit 立即 push**（V2 教训） |
| **架构师 2/8 误判** | V2 #2 文件已删 / #8 已有 19 测试 | M3 subagent 简报**必列已知陷阱**（详见 §0） |
| **ai-trader 教训** | 7 个教训（命中率 > 55% / 复用需 license / markers 必须接通等）| M3 简报必含 `docs/lessons-from-ai-trader.md` 引用 |
| **3 文件 .env 冲突** | V2 pydantic v2 Settings extra=ignore bug | M3 conftest 沿用 `e0bd578`（不扩大改动范围） |

### 🟢 AI-Trader 10 条教训 → M3 自检（V2 §10 #5 强制）

> **来源**：`docs/lessons-from-ai-trader.md` 10 条

| 教训 | M3 关联 | 自检点 |
|---|---|---|
| #1 规范可测试 | M3 3.8 Lighthouse | 量化验收表 7 个 B 指标 |
| #2 信号质量 | M3 3.4 信号标注 | 命中率 > 55% 门禁 |
| #3 数据层先于 AI 层 | M3 配套 backend mock | 必须等 V2 M1.5 K 线 API 就位 |
| #4 TDD 测业务指标 | M3 全部子模块 | 7 个 B 指标脚本是核心 |
| #5 复用需 license | M3 3.6 智能预取 | 借鉴 ai-trader 必须加 license header |
| #6 骨架屏优先 | M3 3.1 路由 + 骨架 | GlassSkeleton 100% 覆盖 |
| #7 后端数据必须前端可视化 | M3 3.3 指标叠加 | 后端 9 个指标前端必须显示 |
| #8 markers 必须接通 | M3 3.4 信号标注 | 不能再"已预留但未接入" |
| #9 暗色模式 | M3 3.0 设计系统 | macOS Sonoma 暗色强制 |
| #10 API 契约先于组件 | M3 3.1 路由 | API client 先于页面组件 |

---

## 0. 预存在问题清单（开工前必读 · V2 教训整合版）

| # | 问题 | 状态 | 影响 | 解决 |
|---|---|---|---|---|
| 0.1 | `prometheus_client` 等 3 个 dep 未装 | ✅ 已修 | 测试可跑 | — |
| 0.2 | `backend/venv/bin/pip` shebang 断 | ✅ 用 `python -m pip` 绕过 | 已知 | subagent 简报必含此命令 |
| 0.3 | **cn/us provider 已砍**（V2 §1 强制）| ✅ v2 落地完成（`8eca690`）| V2 契约 | M3 配套 backend mock 只能用 crypto |
| 0.4 | **默认 market=crypto** | ✅ v2 落地完成 | V2 契约 | M3 前端默认值统一 crypto |
| 0.5 | `test_m3_acceptance.py` 命名误导 | ✅ 已识别，不修改 | 命名陷阱 | subagent 简报必提 |
| 0.6 | 前端 `react-router-dom` 已装但 `main.tsx` 无 `<BrowserRouter>` | 🔧 3.1 修复 | 阻塞 3.1+ | 任务前置 |
| 0.7 | **V2 .env 冲突** | ✅ conftest 已修（`e0bd578`） | 7/7 v2 contract 通过 | subagent 沿用 |
| 0.8 | **V2 cache 阻塞** | ✅ v2 落地已修（`068a47a`）| 已知 | M3 mock 必须用 `try/except 包 cache` |
| 0.9 | `m3-frontend-pages.md` 7 页设计 | ⚠️ **作废** | 与 V2 SPEC 冲突 | M3 plan **不基于此文档** |
| 0.10 | 前端 `App.tsx` 4 tab 旧结构 | 🔧 3.1 改 `<Outlet/>` | 阻塞 | 任务前置 |

---

## 任务分解（按 V2 §M3 子模块顺序，依赖链驱动）

### 阶段 3.0：设计系统（macOS Sonoma tokens）—— V2 §3.0 强制

**V2 SPEC 验收**：tokens.ts 落地（颜色 / 圆角 / 间距 / 字号 / 模糊 / spring）

**步骤 1：subagent 必读文件**（V2 教训 #1：校正节省 50%）
- `SPEC.md` v2 §3.0
- `frontend/src/components/KLineChart/index.tsx`（理解现有颜色/样式使用）
- `frontend/src/App.css`（现有 CSS 变量）
- `frontend/package.json`（确认 Tailwind v4 已装）
- `/opt/ai-trader/frontend/src/styles/tokens.ts`（**只读 UI 模式**，V2 教训 #5：必须加 license header）
- `.cursor/agents/kline-frontend.md`（kline-frontend agent 规范）

**步骤 2：写测试**（V2 §10 #1 强制：业务模块覆盖率 ≥ 80%）
- 文件：`frontend/src/__tests__/tokens.test.ts`
- 测试名：
  - `test_tokens_has_required_color_categories` — 验证 7 大类颜色（background / surface / text / border / accent / success / danger）
  - `test_tokens_respects_macos_sonoma_blur` — 验证 `--blur-glass: 20px` 毛玻璃
  - `test_tokens_spring_physics_constants` — 验证 spring 物理参数（damping/stiffness）

**步骤 3：实现 tokens**
- 文件：`frontend/src/styles/tokens.ts`（新建，~150 行）
- 内容：macOS Sonoma 风格 7 大类 tokens + spring 物理参数 + 暗色强制
- **文件头 license header**（V2 教训 #5）：`// Source: /opt/ai-trader/frontend/src/styles/tokens.ts (inspired, NOT copied)`

**步骤 4：Tailwind 配置**
- 文件：`frontend/tailwind.config.ts`（如不存在则新建）
- 行为：把 tokens 映射到 Tailwind theme

**步骤 5：全局 CSS**
- 文件：`frontend/src/styles/globals.css`（新建）
- 行为：CSS Variables + 暗色背景 + 微噪点（V2 §3.0 强制）

**步骤 6：验证**
- 跑：`cd frontend && npm run typecheck && npm test`
- 期望：0 错 + 9 passed（6 baseline + 3 新增 tokens 测试）

**步骤 7：commit + push**（V2 教训：commit 立即 push）
- `git add frontend/src/styles/ frontend/tailwind.config.ts frontend/src/__tests__/tokens.test.ts`
- `git commit -m "feat(frontend): macOS Sonoma design tokens + tailwind config (M3 3.0)"`
- `git push origin fix/v2-contract-cleanup`（**不累积**）

**步骤 8：完成定义**
- subagent 写 `kbkkk/.cursor/sdd/reports/3.0.md`：含已读文件清单 + 测试输出 + commit hash + push 时间戳

---

### 阶段 3.1：路由 + 骨架（Suspense fallback = GlassSkeleton）—— V2 §3.1

**V2 SPEC 验收**：路由级懒加载（React.lazy + Suspense）+ 100% 骨架屏覆盖（V2 §10 #6 强制）

**步骤 1：subagent 必读**
- `frontend/src/main.tsx`（V2 教训 #0.6：无 BrowserRouter）
- `frontend/src/App.tsx`（V2 教训 #0.10：4 tab 旧结构）
- `frontend/src/components/common/ChartSkeleton.tsx`（参考现有骨架）
- `frontend/package.json`（确认 react-router-dom 7.18.4）
- `frontend/src/components/KLineChart/__tests__/`（测试模式）

**步骤 2：写测试**（≥2 用例）
- `renders KlinePage on / via MemoryRouter`
- `top nav has 3 links`（K线 / 信号 / 设置，V2 §M3 范围只 3 个主要页面）

**步骤 3：实现**
- `frontend/src/main.tsx`：包 `<BrowserRouter>` 在 `<QueryClientProvider>` 外层
- `frontend/src/components/KlineAppShell.tsx`：`<header>` 顶部导航 + `<Outlet/>`
- `frontend/src/App.tsx`：移除 4 tab，改为 `<KlineAppShell>` + `<Routes>`（3 路由：K线 / 信号 / 设置）
- `frontend/src/components/common/PageHeader.tsx`：统一页面头部

**步骤 4：验证 + commit + push**
- 期望：0 错 + 11 passed（6 baseline + 3 tokens + 2 routing）
- `git commit -m "feat(frontend): React Router + 3-page shell + top nav (M3 3.1)"`
- `git push origin fix/v2-contract-cleanup`

---

### 阶段 3.2：K 线主图（lightweight-charts WebGL，1 万根 ≥ 50 FPS）—— V2 §3.2 强制

**V2 SPEC 验收**：1 万根 K 线滚动 ≥ 50 FPS

**步骤 1：subagent 必读**
- `frontend/src/components/KLineChart/index.tsx`（已有，需升级 WebGL）
- `frontend/src/api/klineApi.ts`（VITE_API_BASE 模式）
- `frontend/src/hooks/useKlineData.ts`（数据获取模式）
- `frontend/src/types/kline.ts`（KLineResponse 类型）
- V2 §3.2："lightweight-charts WebGL"
- `lightweight-charts` v5.x 文档（已装 5.2.1）

**步骤 2：写测试**（≥2 用例，含 B3 FPS 业务指标）
- `renders KlineChart with mock kline data`
- **`test_renders_10k_candles_at_50fps`** — 10000 根 mock K 线 + Playwright performance.measure → FPS ≥ 50

**步骤 3：实现**
- `frontend/src/components/KLineChart/index.tsx`：升级用 `createChart` v5 API + WebGL 模式
- 蜡烛图 + 成交量叠加（**V2 crypto 颜色：绿涨红跌**，与 A 股红涨绿跌相反，V2 §crypto 颜色规范）
- 缩放/滚动/十字光标/工具提示
- 包入 `<GlassCard>` 容器（V2 §3.0 毛玻璃）+ 入场 spring 动画

**步骤 4：验证 + B3 业务指标 + commit + push**
- 跑：`./scripts/verify-b3-kline-fps.py --candles 10000 --iterations 10`
- 期望：FPS p50 ≥ 50（否则不通过，V2 §3.2 强制）
- 期望：13 passed（11 + 2 新增）
- `git commit -m "feat(frontend): KLineChart WebGL 10k 50fps (M3 3.2)"`
- `git push origin fix/v2-contract-cleanup`

---

### 阶段 3.3：指标叠加（V2 §3.3 强制 + V2 §10 #7 教训）

**V2 SPEC 验收**：**所有后端指标必须显示**（V2 §10 #7：后端计算了前端必须可视化）

**V2 §M2 指标清单**（9 个）：MA / MACD / RSI / 布林带 / KDJ / OBV / ADX / ATR / Hurst

**步骤 1：subagent 必读**
- `backend/app/routers/analysis.py`（现有 4 端点）
- `frontend/src/api/analysisApi.ts`（现有 client）
- `frontend/src/hooks/useAnalysis.ts`（现有 hook）
- `backend/app/services/indicators.py`（IndicatorEngine 委托 analytics/）
- V2 §3.3 + V2 §10 #7 教训

**步骤 2：写测试**（≥2 用例）
- `renders 9 indicator panels` — 9 个独立 panel 都渲染
- `test_indicator_toggle_visibility` — GlassSegmented 多选切换

**步骤 3：实现**
- `frontend/src/components/IndicatorPanel/index.tsx`：单指标 panel（毛玻璃卡片）
- 9 个指标独立 panel（MA / MACD / RSI / 布林带 / KDJ / OBV / ADX / ATR / Hurst）
- 指标开关控制（GlassSegmented 多选）
- 指标参数可调（周期 / 超买超卖阈值，GlassPopover 弹出）
- Panel 列表入场 stagger 动画（V2 §3.5 准备）

**步骤 4：验证 + B7 自检 + commit + push**
- 跑：`./scripts/verify-b5-ai-trader-lessons.sh --check #7`
- 期望：lesson #7 = "后端数据必须前端可视化" ✅ 9/9 指标可见
- 期望：15 passed（13 + 2 新增）
- `git commit -m "feat(frontend): 9 indicator panels + segmented toggle (M3 3.3)"`
- `git push origin fix/v2-contract-cleanup`

---

### 阶段 3.4：信号标注（markers 必须接通 + WebSocket 推送）—— V2 §3.4 强制

**V2 SPEC 验收**：markers 接口接通（V2 §10 #8 教训：不能再"已预留但未接入"）+ **WebSocket 推送**（hybrid 决策：K线 REST + 信号 WebSocket）

**步骤 1：subagent 必读**
- `frontend/src/components/KLineChart/index.tsx`（3.2 刚升级的版本）
- `frontend/src/hooks/useAnalysis.ts`（现有 useSignals）
- `backend/app/services/event_bus.py`（V2 强制：模块级单例 + DI）
- V2 §3.4 + V2 §10 #8 教训

**步骤 2：写测试**（≥2 用例，含 WebSocket mock）
- `test_renders_signal_markers_on_chart` — mock signals + 验证 markers 出现在 KLineChart
- `test_websocket_signal_arrives_marks_chart` — mock WebSocket 推送 → 验证新 marker 实时出现

**步骤 3：实现**
- `frontend/src/hooks/useSignalWebSocket.ts`（新）：WebSocket 客户端
- `frontend/src/components/SignalMarker.tsx`（新）：箭头 + 浮动标签（spring 弹出动画，0.96 → 1.0 scale）
- 接入 KLineChart：markers API（V2 §10 #8 教训：必须接通，不能"预留"）
- 点击信号查看详情（GlassModal，弹窗 scale+fade 入场）

**步骤 4：验证 + B7 自检 + commit + push**
- 跑：`./scripts/verify-b5-ai-trader-lessons.sh --check #8`
- 期望：lesson #8 = "markers 必须接通" ✅ 实测有 markers 渲染
- 期望：17 passed（15 + 2 新增）
- `git commit -m "feat(frontend): signal markers + WebSocket (M3 3.4)"`
- `git push origin fix/v2-contract-cleanup`

---

### 阶段 3.5：共享元素（layoutId + 入场 stagger）—— V2 §3.5

**V2 SPEC 验收**：layoutId 周期切换 + 入场 stagger 动画

**步骤 1：subagent 必读**
- `frontend/src/components/KLineChart/index.tsx`
- `frontend/src/components/IndicatorPanel/index.tsx`
- `frontend/package.json`（framer-motion 已装）

**步骤 2：写测试**（≥1 用例）
- `test_period_switch_layoutId_animation` — 切换周期触发共享元素动画

**步骤 3：实现**
- 周期选择器（GlassSegmented：1分 / 5分 / 15分 / 60分 / 4h / 1d / 1w）
- 数据重新加载（React Query 缓存 1min staleTime）
- **layoutId 共享元素动画**：周期切换时图表 smooth 过渡（Framer Motion）
- 当前周期高亮（spring 指示器滑动）

**步骤 4：验证 + commit + push**
- 期望：18 passed
- `git commit -m "feat(frontend): shared element period switch (M3 3.5)"`
- `git push origin fix/v2-contract-cleanup`

---

### 阶段 3.6：智能预取（usePrefetchSymbol + ⌘K 命令面板）—— V2 §3.6

**V2 SPEC 验收**：usePrefetchSymbol（hover 150ms 预取）+ ⌘K 命令面板

**步骤 1：subagent 必读**
- V2 §3.6 + V2 §crypto 标的列表（BTC / ETH only）
- `frontend/src/api/klineApi.ts`

**步骤 2：写测试**（≥1 用例）
- `test_prefetch_symbol_on_hover_150ms` — 验证 hover 150ms 后触发 prefetch

**步骤 3：实现**
- `frontend/src/hooks/usePrefetchSymbol.ts`（新）：hover 150ms 防抖预取
- ⌘K / Ctrl+K 命令面板（radix Dialog + Framer Motion scale 弹出）
- 标的搜索 + 跳转（**V2 crypto only**：BTC / ETH）
- 路由级 code splitting（Suspense fallback 用 GlassSkeleton）

**步骤 4：验证 + commit + push**
- 期望：19 passed
- `git commit -m "feat(frontend): usePrefetchSymbol + command palette (M3 3.6)"`
- `git push origin fix/v2-contract-cleanup`

---

### 阶段 3.7：响应式（3 个断点全测）—— V2 §3.7

**V2 SPEC 验收**：3 断点全测（< 768 / 768-1024 / > 1024）

**步骤 1：subagent 必读**
- V2 §3.7 + 现有 CSS 断点

**步骤 2：写测试**（≥1 用例，Playwright 3 视口）
- `test_renders_at_three_breakpoints` — 375 / 834 / 1440 视口截图对比

**步骤 3：实现**
- 移动端适配（断点 < 768 / 768-1024 / > 1024）
- 顶部/底部安全区适配（iPhone notch）

**步骤 4：验证 + commit + push**
- 期望：20 passed
- `git commit -m "feat(frontend): responsive 3 breakpoints (M3 3.7)"`
- `git push origin fix/v2-contract-cleanup`

---

### 阶段 3.8：Lighthouse（性能 ≥ 90 / 无障碍 ≥ 95 / LCP < 2.5s / FPS ≥ 50）—— V2 §3.8 强制

**V2 SPEC 验收**：性能 ≥ 90 / 无障碍 ≥ 95 / LCP < 2.5s / FPS ≥ 50（**V2 强制门禁**）

**步骤 1：subagent 必读**
- V2 §3.8 + V2 §10 #2 强制
- Lighthouse CLI 文档

**步骤 2：写测试**（自动化 B4/B5/B6）
- `scripts/verify-b4-lighthouse.py`：lighthouse CLI 跑主页 → 断言 performance ≥ 90 + accessibility ≥ 95 + LCP < 2.5s

**步骤 3：实现优化**（按 V2 §10 #2 强制）
- Spring 动画 GPU 加速（transform + opacity，避免 width/height 动画）
- React DevTools Profiler 性能瓶颈分析
- 组件懒加载（Heavy 组件：React.lazy + 错误边界）
- Web Vitals 监控埋点

**步骤 4：验证 + B4/B5/B6 业务指标 + commit + push**
- 跑：`./scripts/verify-b4-lighthouse.py --url http://localhost:5173`
- 期望：performance ≥ 90 + accessibility ≥ 95 + LCP < 2.5s（**V2 强制**，否则不通过）
- 期望：21 passed
- `git commit -m "feat(frontend): Lighthouse 90/95/2.5s optimizations (M3 3.8)"`
- `git push origin fix/v2-contract-cleanup`

---

### 阶段 3.9：集成 PR + V2 SPEC §M3 完成定义

**步骤 1：M3 完成定义 checklist**（V2 §M3 + V2 §10 门禁）
- [ ] **B1** 页面首次渲染 p95 < 2.0s
- [ ] **B3** K 线主图 1 万根 ≥ 50 FPS
- [ ] **B4** Lighthouse 性能 ≥ 90
- [ ] **B5** Lighthouse 无障碍 ≥ 95
- [ ] **B6** LCP < 2.5s
- [ ] **B7** AI-Trader 10 教训自检 10/10
- [ ] 9 个指标全部前端可见（V2 §10 #7）
- [ ] markers 接口接通（V2 §10 #8）
- [ ] 骨架屏 100% 覆盖（V2 §10 #6）
- [ ] macOS Sonoma tokens 强制执行（V2 §3.0）
- [ ] V2 教训 8 条强制规则 0 违反
- [ ] BTC/ETH only 文案（V2 §1）
- [ ] 0 个 ai-trader 代码片段被复制（V2 教训 #5：license header 必须）

**步骤 2：M3 PR + auto-merge**
- 走 KBKKK 激进 auto-merge 模式（feature branch + auto-merge.sh）
- engram remember：`kbkkk M3 4 周前端可视化完成 baseline=340+/18+ V2 §M3 7/7 验收`

---

## 文件结构（V2 §M3 子模块映射）

```
frontend/src/
├── styles/                                 # ★ 3.0 新增
│   ├── tokens.ts                           # macOS Sonoma tokens
│   ├── fonts.ts                            # SF Pro Display 字体集成
│   ├── animations.ts                       # 统一动画 variants
│   └── globals.css                         # CSS Variables + 暗色 + 微噪点
├── components/
│   ├── ui/                                 # ★ 3.0 新增（玻璃组件库）
│   │   ├── GlassCard.tsx
│   │   ├── GlassButton.tsx
│   │   ├── GlassModal.tsx
│   │   ├── GlassSkeleton.tsx
│   │   ├── GlassTabs.tsx
│   │   ├── GlassSegmented.tsx
│   │   ├── GlassPopover.tsx
│   │   └── CommandPalette.tsx              # ★ 3.6
│   ├── KlineAppShell.tsx                   # ★ 3.1
│   ├── common/
│   │   ├── PageHeader.tsx                  # ★ 3.1
│   │   ├── ErrorMessage.tsx
│   │   ├── ChartSkeleton.tsx               # 升级为 GlassSkeleton
│   │   └── EmptyState.tsx
│   ├── KLineChart/
│   │   ├── index.tsx                       # ← 3.2 升级（WebGL 10k 50fps）
│   │   ├── SignalMarker.tsx                # ★ 3.4
│   │   └── PeriodSwitcher.tsx              # ★ 3.5
│   └── IndicatorPanel/
│       ├── index.tsx                       # ★ 3.3（9 指标 panel）
│       └── IndicatorToggle.tsx             # ★ 3.3
├── hooks/
│   ├── useKlineData.ts
│   ├── useAnalysis.ts
│   ├── usePrefetchSymbol.ts                # ★ 3.6
│   └── useSignalWebSocket.ts               # ★ 3.4
├── pages/                                  # ★ 3.1+ 新增
│   ├── KlinePage.tsx                       # 3 个主页面之一
│   ├── SignalsPage.tsx                     # 3 个主页面之一
│   └── SettingsPage.tsx                    # 3 个主页面之一
├── api/
│   └── signalWebSocket.ts                  # ★ 3.4
├── App.tsx                                 # ← 3.1 改 <Outlet/>
├── main.tsx                                # ← 3.1 加 <BrowserRouter>
├── types/
│   ├── kline.ts
│   └── analysis.ts
└── __tests__/
    ├── tokens.test.ts                      # ★ 3.0
    ├── App.routing.test.tsx                # ★ 3.1
    ├── KLineChart.fps.test.tsx             # ★ 3.2 (B3)
    ├── IndicatorPanel.test.tsx             # ★ 3.3
    ├── SignalMarker.test.tsx               # ★ 3.4
    ├── PeriodSwitcher.test.tsx             # ★ 3.5
    ├── usePrefetchSymbol.test.ts           # ★ 3.6
    └── responsive.test.tsx                 # ★ 3.7 (3 断点)
```

```
scripts/                                    # ★ M3 新增
├── verify-b1-page-load.py                  # B1
├── verify-b2-signal-latency.py             # B2
├── verify-b3-kline-fps.py                  # B3
├── verify-b4-lighthouse.py                 # B4/B5/B6
└── verify-b5-ai-trader-lessons.sh          # B7
```

---

## 自检清单（写完计划必走 + V2 教训强化）

- [x] **V2 宪法对齐**：完全基于 SPEC v2.0 §M3，**不再基于 m3-frontend-pages.md**
- [x] **V2 范围**：9 个子模块（3.0-3.8），4 周时间，与 M2 并行
- [x] **V2 量化验收**：每个子模块引用 SPEC §M3 验收项
- [x] **metrics-first**：7 个 B 指标（B1-B7）必测不通过即返工
- [x] **V2 校正节省 50%**：subagent 必读 SPEC §M3 + 6 文件清单
- [x] **V2 风险优先**：任务顺序按 V2 §M3 依赖链（3.0→3.1→3.2→3.3→3.4→3.5→3.6→3.7→3.8）
- [x] **V2 架构边界**：M3 前端代码按 V2 §M3.0 设计系统强制
- [x] **V2 AsyncClient 绕开**：M3 mock 用 ASGITransport 模式
- [x] **V2 commit 立即 push**：每 commit 立即 push 不累积
- [x] **V2 AI-Trader 10 教训**：B7 自检 + 引用 `docs/lessons-from-ai-trader.md`
- [x] **V2 架构师 2/8 误判**：subagent 简报必列已知陷阱
- [x] **BTC/ETH only**：所有 UI 文案 / 默认值 / 标的列表聚焦 BTC + ETH
- [x] **0 ai-trader 复制**：借鉴 UI 模式必须加 license header
- [x] **业务指标先行**：B1-B7 脚本不是技术指标而是业务指标（FPS / Lighthouse / LCP）
- [x] **任务独立**：每个任务能独立提交
- [x] **时间预算**：每任务 < 1 周工作量

## 执行方式

**SDD**（子代理驱动），按 `sdd.mdc` 流程：

```
worktree 前端  /private/tmp/kbkkk-m3-frontend -b feat/m3-frontend-v2-spec
                              ↓
              3.0 subagent（设计系统 macOS Sonoma tokens）
                              ↓ 等 merge
              3.1 subagent（路由 + 骨架）
                              ↓
              3.2-3.7 subagent（可串行或部分并行）
                              ↓
              3.8 subagent（Lighthouse 强制门禁）
                              ↓
              3.9 集成 PR + 7 B 指标全验证
```

**前置依赖**：
- ✅ v2 落地 commit `8eca690` 已合（或在 fix/v2-contract-cleanup 分支）
- ✅ v2 conftest 修复 `e0bd578` 已合
- ✅ V2 contract 测试 7/7 通过
- ⏳ **下一步**：v2 合 main + 开 M3 worktree

**简报位置**（按 `sdd.mdc` 模板）：
- `kbkkk/.cursor/sdd/briefs/3.X.md` — 每个子任务（含"必读 SPEC §M3.X + 6 文件 + 已读断言 + V2 教训相关段"）
- `kbkkk/.cursor/sdd/reports/` — subagent 报告（含"已读文件清单 + 测试输出 + B 指标数字 + commit hash + push 时间戳"）
- `kbkkk/.cursor/sdd/progress.md` — 账本（含"V2 SPEC §M3 完成进度 + 7 B 指标通过情况"）

## V2 教训对账表（最终自检）

| V2 教训（source: SPEC-v2-round1-completion-report §7 + lessons-from-ai-trader）| M3 整合位置 | 状态 |
|---|---|---|
| 7.1 校正节省 50% | subagent 必读文件清单（每个任务 §步骤 1）| ✅ |
| 7.1 PR 按风险排序 | 任务顺序按 V2 §M3 依赖链 | ✅ |
| 7.2 校正步骤价值 | subagent 简报"已知陷阱"段（§0）| ✅ |
| 7.3 测试环境兼容 | conftest.py 沿用 `e0bd578` | ✅ |
| 7.4 commit 立即 push | 每任务 §步骤 N：git push | ✅ |
| 7.5 SPEC 文档治理 | 任务表含 commit hash + push timestamp | ✅ |
| 7.5 文档与代码同步 | progress.md 含 V2 对账表（此表）| ✅ |
| AI-Trader #1 规范可测试 | B1-B7 量化指标 | ✅ |
| AI-Trader #2 信号 > 55% | B7 自检引用 | ✅ |
| AI-Trader #4 TDD 测业务指标 | B1-B7 业务指标脚本 | ✅ |
| AI-Trader #5 复用需 license | "借鉴 UI 模式必须加 license header" | ✅ |
| AI-Trader #6 骨架屏优先 | 3.1 路由 + 3.0 GlassSkeleton 100% 覆盖 | ✅ |
| AI-Trader #7 后端数据前端可视化 | 3.3 9 指标全部前端可见 | ✅ |
| AI-Trader #8 markers 必须接通 | 3.4 信号标注强制接通 | ✅ |
| AI-Trader #9 暗色模式 | 3.0 macOS Sonoma 暗色强制 | ✅ |
| AI-Trader #10 API 契约先于组件 | 3.1 路由 + API client 先于页面 | ✅ |
| V2 §1 BTC/ETH only | 全文案 + 默认值 + 标的列表 | ✅ |
| V2 §3.0-3.8 9 子模块 | 9 任务一一对应 | ✅ |
| V2 §10 #1-7 质量门禁 | B1-B7 + 工程指标 | ✅ |
