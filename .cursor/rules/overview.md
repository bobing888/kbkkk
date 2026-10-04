# kbkkk 项目级 Rule 总览

> **适用**：kbkkk 仓库内所有 AI agent / IDE 自动加载
> **来源**：kbkkk AGENTS.md + .cursor/rules/ + engram MCP

---

## 🧠 必用 engram MCP 工具

> **engram = 本地私有记忆层，跨会话/跨工具共享 kbkkk 项目知识（2518+ chunks）**
> 你有 4 个 engram MCP 工具，开工前 recall 必跑、完工后必须 remember：

| 工具 | 调用方式 | 何时用 |
|------|----------|--------|
| `engram_recall` | `mcp__engram__engram_recall({query, limit, since})` | 开工前查 kbkkk 历史决策 / 已有架构 / 踩过的坑 |
| `engram_status` | `mcp__engram__engram_status({})` | 不确定 engram 健康时 |
| `engram_remember` | `mcp__engram__engram_remember({text, source, date})` | 关键决策 / 重要发现沉淀 |
| `engram_reinforce` | `mcp__engram__engram_reinforce({query, source})` | 确认 recall 答案来源，自学习 |

**kbkkk workflow**：

```javascript
// 1. 开工前 — 必跑
mcp__engram__engram_recall({
  query: "kbkkk <本任务关键词，如 'MACD 策略' / '回测' / 'API 设计'>",
  limit: 5
})

// 2. 完工后 — 必跑
mcp__engram__engram_remember({
  text: "<关键决策 + 为什么 + 不变量>",
  source: "<agent-name>",
  date: "2026-10-04"
})
```

**何时不用**：外部世界知识（股价/新闻/API 文档）—— engram 只有本地记忆。

---

## 📋 kbkkk 工作流（总览）

### 自动合并（kbkkk 激进模式）

```
feature branch 改动
   ↓ git commit
post-commit hook
   ├─ Step 1: auto-merge.sh
   │     → git push + PR 草稿 + 启用 auto-merge
   └─ Step 2: engram ingest（保险网）
         → 同步 AGENTS.md + rules + workflows + scripts
   ↓
GitHub Actions: smoke:check 必过
   ↓
auto-merge 自动 squash 合到 main
   ↓
engram watcher 实时索引新文件
```

**禁止**：在 main 上 commit（branch protection + enforced-gate 拦）

### kbkkk 提交规范

- commit message：`feat(scope): ...` / `fix(scope): ...` / `docs(scope): ...`
- branch 名：`feature/xxx` / `fix/xxx`
- PR base：main
- 单 PR ≤ 500 行

---

## 🚪 与 engram 协作的失败模式

| 红线 | 为什么 | 怎么办 |
|------|--------|--------|
| 不查 engram 就干活 | 重复发明 / 踩过的坑再踩 | 开工前必 recall |
| 完工不沉淀 | 跨会话忘 | 完工后必 remember |
| 强制抹除 engram | 失去记忆 | reinforce / forget 要确认 |

---

## 🎯 kbkkk 当前可用 Agent

| Agent | 何时用 |
|-------|--------|
| `@kbkkk-kline-backend` | 后端 API / 数据库 / 数据获取 |
| `@kbkkk-kline-analyst` | K 线分析 / 技术指标 / 策略 |
| `@kbkkk-kline-frontend` | 前端图表 / UI |
| `@kbkkk-kline-orchestrator` | 多 agent 协调 |
| `@kbkkk-kline-pm` | 项目管理 / roadmap |
| `@kbkkk-backend-architect` | 后端架构 / ADR |
| `@kbkkk-frontend-developer` | 前端架构 |
| `@kbkkk-api-tester` | 测试 |
| `@kbkkk-devops` | 部署 / CI/CD / 监控 |

所有 agent 都会**自动**先 engram_recall 再开干。

---

## 版本历史

- v1（2026-10-04）：kbkkk 专属版 + engram MCP 集成