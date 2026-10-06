# SPEC v2 第一轮部署 Checklist

> 给部署对话 `28e6a715-add0-4baa-9e60-36fd5d80d39f` 用
> 假设你已经知道 kbkkk 的部署流程，本 checklist 仅覆盖 SPEC v2 增量项

## 1. 准备：要合并的 4 个 PR

| PR | Commit | 优先级 | 合并顺序 |
|---|---|---|---|
| PR-1 | `2258236` (已存在 main) | 1 | 已合并 |
| PR-2 | `c114a88` (branch: `refactor/spec-v2-pr2-follow-async-ccxt-reuse`) | 2 | 第一个合并 |
| PR-3 | `041293c` (branch: `refactor/spec-v2-pr3-sqlite-adapter`) | 3 | 第二个合并 |
| PR-4 | `068a47a` (branch: `refactor/spec-v2-pr4-kline-cache-resilience`) | 4 | 第三个合并 |

**为什么这个顺序**：
- PR-2 风险最高（事件循环重构）
- PR-3 风险低（driver 切换）
- PR-4 风险最低（10 行 try/except）

**合并命令**（在 kbkkk 仓库）：
```bash
cd /path/to/kbkkk
git checkout main

# PR-2
git merge --no-ff refactor/spec-v2-pr2-follow-async-ccxt-reuse -m "merge: SPEC v2 PR-2 (follow async + ccxt 复用)"
# 解决可能冲突 → git add → git commit

# PR-3
git merge --no-ff refactor/spec-v2-pr3-sqlite-adapter -m "merge: SPEC v2 PR-3 (SQLite 适配)"

# PR-4
git merge --no-ff refactor/spec-v2-pr4-kline-cache-resilience -m "merge: SPEC v2 PR-4 (cache 不阻塞 API)"

# 验证
git log --oneline -8
# 应看到 3 个 merge commit
```

## 2. 部署：环境变量配置

### 2.1 新增环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `DB_BACKEND` | `postgres` | dev/test 设 `sqlite` |
| `SQLITE_PATH` | `./data/kline.db` | SQLite 文件路径 |
| `KBKKK_CRYPTO_EXCHANGE` | `okx` | 新增（PR-2 引入） |

### 2.2 dev/test 部署（推荐）

```bash
# .env
DB_BACKEND=sqlite
SQLITE_PATH=./data/kline.db
KBKKK_CRYPTO_EXCHANGE=okx

# 启动
cd /path/to/kbkkk/backend
pip install -r requirements.txt   # 装 aiosqlite
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**首次启动会自动创建**：
- `./data/kline.db` (SQLite 文件，含 7 张表)
- `/api/v1/kline/...` 路由
- `/api/v1/health` endpoint

### 2.3 生产部署（保持 PG）

```bash
# .env
DB_BACKEND=postgres
DATABASE_URL=postgresql+asyncpg://...   # 已有
KBKKK_CRYPTO_EXCHANGE=okx

# 启动
cd /path/to/kbkkk/backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**PG 行为不变**：
- 仍创建 `uuid-ossp` / `pg_trgm` 扩展
- 7 张表用 `create_all` 幂等创建
- 不需要 Alembic 迁移

## 3. 验证步骤（合并部署后必做）

### 3.1 服务启动

```bash
# 后台启动
uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
sleep 3

# 检查日志
tail -20 /tmp/uvicorn.log
# 期望看到:
#   [db] backend=sqlite, url=sqlite+aiosqlite:///./data/kline.db
#   Database tables created/verified (backend=sqlite)
#   Application startup complete
```

### 3.2 健康检查

```bash
curl http://localhost:8000/api/v1/health
# 期望: {"status":"ok","database":"ok","redis":"ok"}
# 或:   {"status":"degraded","database":"ok","redis":"down"}  (若 Redis 未起)
```

### 3.3 K线 endpoint

```bash
# 加密货币（用 OKX 默认）
curl "http://localhost:8000/api/v1/kline/BTCUSDT?period=1d&market=crypto"
# 期望: 200, JSON, source: "fresh" 或 "cache"

# A股
curl "http://localhost:8000/api/v1/kline/600519?period=1d&market=cn"
```

### 3.4 失败注入测试（验证 PR-4 防御）

```bash
# 停 Redis
docker stop redis    # 或 kill redis-server

# 重新请求 K线
curl "http://localhost:8000/api/v1/kline/BTCUSDT?period=1d&market=crypto"
# 期望: 仍返回 200（cache 失败不阻塞 API）
# 日志会有: "Cache write failed for kbkk:...:kline:BTCUSDT:1d:..."
```

### 3.5 ccxt 复用（验证 PR-2）

```bash
# 在浏览器或 docs 页面打开
http://localhost:8000/docs
# 找 /api/v1/kline/{symbol} → 试 "Execute" 几次
# 观察 ccxt 单例只在首次请求时建连接

# 或看日志: ccxt 不应每次都 "Connecting to okx..."
```

## 4. 回归测试（部署后跑一次）

```bash
cd /path/to/kbkkk/backend
python3 -m pytest tests/ --ignore=tests/test_health_endpoint.py \
                        --ignore=tests/test_metrics.py \
                        --ignore=tests/test_m3_acceptance.py
# 期望: 347 passed
```

**已 ignore 的 3 个文件**：与 .env `GRAFANA_PASSWORD` 冲突（**已有 bug，不在 SPEC v2 范围**）

## 5. 部署完成报告

请在部署对话中报告以下信息：

```
部署对话 ID: 28e6a715-add0-4baa-9e60-36fd5d80d39f
部署目标: kbkkk.com
合并 commit:
  - PR-2: <merge-commit-hash>
  - PR-3: <merge-commit-hash>
  - PR-4: <merge-commit-hash>
部署模式: [sqlite | postgres]
启动时间: <timestamp>
健康检查: <200/500/timeout>
K线 endpoint: <200/500/timeout>
回归测试: <passed count> passed
已知问题: <如有>
```

## 6. 回滚预案（如部署失败）

```bash
# kbkkk 仓库
git revert -m 1 <merge-commit-hash>   # 逐个回滚
# 或
git reset --hard <last-good-commit>  # 强制回滚

# 重启服务
pkill -f uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

**注意**：`git reset --hard` 会丢失未推送的 commit——本对话已确保 4 个 PR 全部推送到 origin，回滚可逆。

## 7. 关联资源

| 资源 | 位置 |
|---|---|
| 完成报告 | `docs/SPEC-v2-round1-completion-report.md` |
| 任务清单 | `docs/refactor-spec-v2-tasks.md` |
| 远端 branches | `bobing888/kbkkk` repo, 4 个 `refactor/spec-v2-pr*` 分支 |
| 本对话 | 当前对话（代码 + 测试） |
| 部署对话 | `28e6a715-add0-4baa-9e60-36fd5d80d39f`（本 checklist） |

---

**checklist 完成时间**：2026-10-06 14:20
**作者**：Cursor Assistant (kline-architect)