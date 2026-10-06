# kbkkk M4 K线图组件 — 技术决策记录

## 技术栈
- Vite + React 19 + TypeScript strict (noUncheckedIndexedAccess: true)
- lightweight-charts v5（不是 v4）
- TanStack Query v5 + Zustand + Tailwind v4 + Vitest

## 组件结构
```
src/
├── components/
│   ├── KLineChart/
│   │   ├── index.tsx          # 主组件：4态（loading/error/empty/success）
│   │   └── __tests__/
│   │       └── KLineChart.test.tsx
│   └── common/
│       ├── ChartSkeleton.tsx  # 毛玻璃骨架屏
│       ├── ErrorMessage.tsx   # 错误态
│       └── EmptyState.tsx     # 空数据态
├── api/
│   └── klineApi.ts            # fetchKLine API
├── hooks/
│   └── useKlineData.ts        # TanStack Query hook
└── types/
    └── kline.ts               # KLineData / CandlestickData 类型
```

## 踩过的坑

### 1. lightweight-charts v5 API 变更
- ❌ v4: `chart.addCandlestickSeries()`
- ✅ v5: `chart.addSeries(CandlestickSeries)`
- 必须同时 import `CandlestickSeries` + `CandlestickData<Time>` + `Time` 类型

### 2. noUncheckedIndexedAccess 让数组 map 变严格
- `data.map(k => k.datetime)` 中 `k` 类型变成 `KLineData | undefined`
- 运行时访问 `.datetime` 报错：`Cannot read properties of undefined`
- 解法：在 `.map` 中加 defensive check：`if (!k || typeof k.datetime !== 'string') return null`
- 根本解法：创建 `tsconfig.test.json` 对测试关闭 `noUncheckedIndexedAccess`

### 3. Vitest mock 缺少 v5 API
- 测试 mock 必须导出 `CandlestickSeries` + `addSeries`
- 必须安装 `resize-observer-polyfill` 并在 `setupTests.ts` 全局注册

### 4. ChartSkeleton Math.random() lint warning
- oxlint 报 purity warning：`Math.random` 是 impure function
- 解法：定义固定 `HEIGHTS` 数组替代

## 不变量
- chart.remove() 必须在 useEffect cleanup 中调用（内存泄漏防护）
- 后端 API 字段名是 `datetime` 不是 `time`
- 指标通过 `props.indicators` 控制，不硬编码

## 下一步
1. IndicatorPanel 指标切换组件
2. PatternBadge 形态标注（markers 接口）
3. KLinePage 路由层 + Zustand store
4. macOS Sonoma tokens.ts 设计系统
