# kbkkk Auto-Merge 强制规则

进入 kbkkk 仓库时，以下规则必须遵守。

## 工作流

1. **永远不在 main 上直接 commit**。先 `git checkout -b feature/xxx` 或 `fix/xxx`。
2. **commit 后让 hook 跑**。hook 在 `.git/hooks/post-commit`，会自动跑 `~/.local/bin/auto-merge.sh`。
3. **不要手动 push 到 main**。enforced-gate 会拦，且 branch protection 不允许。
4. **PR 等 smoke check 后自动合**。不要手动 squash merge。
5. **commit message 标 type 前缀**（feat/fix/docs/refactor/test/chore）。

## 禁止 force push 到 main

即使 git 允许，**禁止** main 分支 force push / reset。

## 大改动先拆 PR

> 500 行或 5+ 文件 → 拆 PR；不要一个 mega PR。

## 自检

agent 提交前自问：

- [ ] 在 feature branch 上？
- [ ] commit message 合规？
- [ ] 没大文件 / .env / 凭据？
- [ ] 有没有手动跑 post-commit hook？

## 🧠 kbkkk 可用 MCP 工具

> **engram = 本地私有记忆层，跨会话/跨工具共享 kbkkk 项目知识**

| 工具 | 调用方式 | 何时用 |
|------|----------|--------|
| `engram_recall` | `mcp__engram__engram_recall({query, limit, since})` | 开工前查 kbkkk 已有架构 / 决策 / 踩过的坑 |
| `engram_status` | `mcp__engram__engram_status({})` | 不确定 store 健康时 |
| `engram_remember` | `mcp__engram__engram_remember({text, source, date})` | 关键决策 / 重要发现沉淀 |
| `engram_reinforce` | `mcp__engram__engram_reinforce({query, source})` | 确认 recall 答案，自学习 |

**kbkkk 专属 workflow**：

```javascript
// 1. 开工前 — 查 kbkkk 已有决策
mcp__engram__engram_recall({
  query: "kbkkk <本任务关键词>",
  limit: 5
})

// 2. 完工后 — 沉淀决策
mcp__engram__engram_remember({
  text: "<关键决策 + 为什么>",
  source: "<agent-name>",
  date: "2026-10-04"
})
```
