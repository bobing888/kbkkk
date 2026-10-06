#!/bin/bash
# K4 M4 SRE: auto-follow-worker 启动脚本
# 用法: ./scripts/run-worker.sh
set -e

echo "[run-worker] Starting auto-follow-worker..."
exec python -m app.follow.follow_worker
