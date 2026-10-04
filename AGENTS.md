# AGENTS.md —— kbkkk 项目 AI 协作规则

> 本文件供 AI agent 阅读。CLAUDE.md / GEMINI.md 是别名。
> 凡是向 kbkkk 提交代码的 agent 必读。

## 🚦 自动合并工作流

kbkkk 使用 **激进自动合并** 模式：

```
feature branch 改动
   ↓ git commit
post-commit hook (local)
   ↓ auto-merge.sh
push + PR 草稿创建
   ↓
GitHub Actions: smoke:check（必过）
   ↓
enablePullRequestAutoMerge (squash)
   ↓
PR 合入 main + engram 更新
```

**前提**：所有改动必须从 feature branch 发起（`feature/*` / `fix/*` / `docs/*` / `refactor/*`）。
**禁止**直接在 `main` 上 commit —— enforced-gate 会拦。

## ✅ 允许 agent 自动做的事

1. **git commit**：commit message 写清楚 `feat:` / `fix:` / `docs:` / `refactor:` 前缀
2. **git push**：推送到远端 feature branch
4. **创建 PR 草稿**：`gh pr create --base main --draft` 或直接创建
5. **squash auto-merge**：等 smoke:check 通过后自动合
7. **更新 engram**：`~/.engram/store.json`（commit 触发 watcher 自动更新）
3. **git pull / fetch**：拉远端最新

## ❌ 禁止 agent 自动做的事

1. ❌ force-push 到 main（branch protection 拦）
2. ❌ 在 main 上直接 commit（branch protection + enforced-gate 拦）
3. ❌ 跳过 smoke check 合 PR（required status 拦）
4. ❌ `--no-verify` 跳过 git hooks（除非紧急）
5. ❌ 删 PR 评论（破坏审计）
6. ❌ 大文件 / 凭据 / .env 提交（用 .gitignore 过滤）

## 📋 提交规范

- **commit message**：用 conventional commits（feat/fix/docs/refactor/test/chore）
- **PR title**：同 commit message 前缀
- **PR body**：说明 what/why/不变量，3 步以上
- **branch 名**：`feature/xxx` / `fix/xxx` / `docs/xxx`

## 🔧 必需工具

```bash
# 用户态
which gh        # GitHub CLI
which autos-merge                  # 本地 auto-merge.sh（post-commit hook 自动跑）
ls ~/.cursor/hooks.json       # Cursor 规则
```

## 🆘 失败恢复

| 症状 | 原因 | 解法 |
|------|------|------|
| "smoke:check required" | PR 必须 up-to-date | `gh pr update-branch` 或 rebase |
| "PR #N CONFLICTING" | 与 main 有冲突 | rebase main 后 push --force-with-lease |
| post-commit hook 没触发 | 手工 commit 或别处加的 | `bash ~/.git/hooks/post-commit` 手动跑 |
| "enforced-gate 拒绝" | 在 main 上 push | 切到 feature branch 再来 |

