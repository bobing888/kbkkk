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
