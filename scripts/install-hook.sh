#!/bin/bash
# install-hook.sh —— 在 kbkkk 仓库内安装 post-commit auto-merge hook
# 用法: bash scripts/install-hook.sh
set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOK_PATH="$REPO_ROOT/.git/hooks/post-commit"

if [ -f "$HOOK_PATH" ] && [ "$1" != "--force" ]; then
    echo "post-commit hook 已存在，用 --force 覆盖"
    exit 0
fi

cat > "$HOOK_PATH" <<'HOOKEOF'
#!/bin/bash
# post-commit hook —— commit 后调 auto-merge.sh
# 配套 AGENTS.md 和 .cursor/rules/auto-merge.md
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export MAIN_BRANCH="main"
export REMOTE="origin"
export AUTO_MERGE_LOG="$HOME/.engram/auto-merge.log"
exec bash ~/.local/bin/auto-merge.sh
HOOKEOF

chmod +x "$HOOK_PATH"
echo "✓ post-commit hook 已安装: $HOOK_PATH"
echo "✓ 下次 commit 会自动 push / 合 PR"
