# kbkkk 代码规范

## Conventional Commits

```
feat(scope): 新功能
fix(scope): bug 修复
docs(scope): 文档
refactor(scope): 重构
test(scope): 测试
chore(scope): 杂项
```

## PR 规则

- base 总是 main
- title 跟 commit message 一致（squash 合并会用 title）
- body 至少含：what / why / 不变量
- 单 PR 不超过 500 行（拆分参考）

## 文件命名

- Python: `snake_case.py`
- TS/JS: `camelCase.ts` / `PascalCase.tsx`
- MD: 标题用 `## 标题` 二级起

## 🧠 kbkkk 可用 MCP 工具

> **engram = 本地私有记忆层，跨会话/跨工具共享 kbkkk 项目知识**

| 工具 | 调用方式 | 何时用 |
|------|----------|--------|
| `engram_recall` | `mcp__engram__engram_recall({query, limit, since})` | 开工前查 kbkkk 已有规范 / 历史 |
| `engram_status` | `mcp__engram__engram_status({})` | 不确定 store 健康时 |
| `engram_remember` | `mcp__engram__engram_remember({text, source, date})` | 关键规范决策沉淀 |
| `engram_reinforce` | `mcp__engram__engram_reinforce({query, source})` | 确认 recall 答案 |

**典型用法**：

```javascript
mcp__engram__engram_recall({ query: "kbkkk 命名规范 文件结构", limit: 5 })
mcp__engram__engram_remember({ text: "<规范决策>", source: "kbkkk-conventions", date: "2026-10-04" })
```
