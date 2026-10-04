#!/bin/bash
# install-hook.sh —— 在 kbkkk 仓库内安装 post-commit auto-merge + engram sync hook
# 用法: bash scripts/install-hook.sh
#       bash scripts/install-hook.sh --force  # 覆盖已存在 hook
set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOK_PATH="$REPO_ROOT/.git/hooks/post-commit"

if [ -f "$HOOK_PATH" ] && [ "$1" != "--force" ]; then
    echo "post-commit hook 已存在，用 --force 覆盖"
    exit 0
fi

cat > "$HOOK_PATH" <<'HOOKEOF'
#!/bin/bash
# kbkkk post-commit hook —— commit 后自动
#   1. push 远端 + 创建/更新 PR + 启用 auto-merge
#   2. 同步 engram（保险网，防止 watcher 漏）
# 配套 AGENTS.md + .cursor/rules/auto-merge.md

# 显式设 PATH（git hook 继承最小 env）
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# ─── 1. Auto-merge: push + PR + auto-merge ───
export MAIN_BRANCH="main"
export REMOTE="origin"
export AUTO_MERGE_LOG="$HOME/.engram/auto-merge.log"
bash ~/.local/bin/auto-merge.sh

# ─── 2. Engram 同步（保险网）───
# watcher 已在 watch kbkkk 的 AGENTS.md + rules/ + workflows/ + scripts/
# 这里用 engram ingest 强制同步（增量，只处理变化文件）
ENGRAM_PATHS=(
    "$REPO_ROOT/AGENTS.md"
    "$REPO_ROOT/.cursor/rules/"
    "$REPO_ROOT/.github/workflows/"
    "$REPO_ROOT/scripts/"
    "$REPO_ROOT/README.md"
    "$REPO_ROOT/SPEC.md"
)
EXISTING_PATHS=()
for p in "${ENGRAM_PATHS[@]}"; do
    [ -e "$p" ] && EXISTING_PATHS+=("$p")
done
if [ ${#EXISTING_PATHS[@]} -gt 0 ]; then
    /opt/homebrew/bin/engram ingest "${EXISTING_PATHS[@]}" \
        >> "$HOME/.engram/auto-merge.log" 2>&1 || true
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] [engram] synced ${#EXISTING_PATHS[@]} paths" \
        >> "$HOME/.engram/auto-merge.log"
fi
HOOKEOF

chmod +x "$HOOK_PATH"
echo "✓ post-commit hook 已安装: $HOOK_PATH"
echo ""
echo "  下次 commit 会自动："
echo "    1. push origin feature/xxx"
echo "    2. 创建 PR（如没有）"
echo "    3. 启用 auto-merge（squash）"
echo "    4. 同步 kbkkk 文档到 engram"
