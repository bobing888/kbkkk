# SPEC v2 技术债校正任务清单（PR-2 之后）

> **日期**: 2026-10-06
> **状态**: 校正版（基于实际代码状态修订，非 kbkkk-architect-review.md 原表）
> **对应**: [SPEC v2 §v2 立即可执行技术债清单](../SPEC.md)
> **修订依据**:
> - PR #14 已完成 #4（redis degradation）和「async/sync split」（`signal_service.go` 全文件删除 + 同步 Session 走 executor）
> - PR #17 已完成 services.indicators ↔ analytics 循环依赖解除（IndicatorEngine 薄封装）
> - analytics/ **已有 19 个测试文件**（Arch §5 #8 误判）
> - `follow_engine.py:184` 仍 `asyncio.run()`（Arch §5 #3 未做）

---

## 校正版任务表（v2.0 修订 — 2026-10-06 更新）

| # | 原始 Arch 项 | 真实状态 | 行动 | Commit |
|---|---|---|---|---|
| 1 | `_calc_obv` Python for 循环 | ✅ **已完成**（`2258236`，2026-10-06 13:02）| 无 | `2258236` |
| 2 | `signal_service.py:69` 内联 `AnalyticsEngine()` | ❌ **no-op**：文件已删（PR #14 + squash 后被吞并）| 无 | — |
| 3 | `follow_engine.py:184` `asyncio.run()` 在同步方法 | ✅ **已完成**（PR-2A）| **PR-2A** | `c114a88` |
| 4 | cache.py Redis 失败抛异常 | ✅ **已完成**（`2258236`，含 `_is_available()` 守卫 + `client = None`）| 无 | `2258236` |
| 5 | `db.py` 仅 PostgreSQL | ❌ 未做 | **PR-3** | — |
| 6 | `data_fetcher.py:252` 每次新 `ccxt.binance()` | ✅ **已完成**（PR-2B）| **PR-2B** | `c114a88` |
| 7 | `routers/kline.py:39-42` `cache_set` 失败阻塞 API | ❌ 未做 | **PR-4A** | — |
| 8 | analytics/ 无单元测试 | ❌ **误判**：已有 19 个测试 | 无 | — |

**校正要点**：
- 原始 8 项 → 真实剩 4 项有效工作（#3、#5、#6、#7）
- #1 + #4 已在 commit `2258236`（PR-1 实际状态）
- #2 + #8 是 Arch 报告错误，no-op
- **截至 2026-10-06 13:35**: #3 + #6 已在 `c114a88` 完成
- 剩余真实工作量: **2 项**（#5 SQLite 1 天 + #7 cache 不阻塞 半天 = 1.5 天）

---

## PR-2: follow_engine async 化 + ccxt 连接复用（1 天）

> **目标**: 消除事件循环嵌套 + 减少 ccxt 连接开销。

### PR-2A: follow_engine 异步化（0.5 天）

**位置**: `backend/app/follow/follow_engine.py:184`

**现状**：
```python
def on_market_update(self, current_prices):  # 同步方法
    ...
    return asyncio.run(self._on_market_update_async(current_prices))  # ❌ 嵌套事件循环
```

**改造**：
- `on_market_update` 改 `async def`
- 删除 `asyncio.run()`
- 上层 caller（`follow_worker.py`）相应改 `await`

**验证**：
- `pytest backend/tests/test_follow_engine.py -x` 4 项通过
- 新增 1 项测试：连续 10 次 `on_market_update` 不报错（防 future 内 raise）

**KB 参考**: vibetrading-implementation-ready.md §"async hook for periodic tasks"

### PR-2B: ccxt 连接复用（0.5 天）

**位置**: `backend/app/data/data_fetcher.py:290` 附近

**现状**：
```python
exchange = ccxt.binance({"enableRateLimit": True})  # 每次 fetch 都新建
```

**改造**：
```python
# 模块级单例 + 缓存（class-level）
_EXCHANGE_CACHE: dict[str, ccxt.Exchange] = {}

def _get_exchange(name: str) -> ccxt.Exchange:
    if name not in _EXCHANGE_CACHE:
        _EXCHANGE_CACHE[name] = getattr(ccxt, name)({"enableRateLimit": True})
    return _EXCHANGE_CACHE[name]
```

**验证**：
- 100 次连续 fetch，时间 < 单次 fetch * 50（连接复用应 < 50 倍开销）
- 已有 `test_data_fetcher.py` 通过

**KB 参考**: vibetrading-implementation-ready.md §"Lazy provider registry"

---

## PR-3: SQLite 适配（降低开发门槛）（1 天）

> **目标**: dev 环境无需 PostgreSQL，单文件 DB 即可跑后端。

**位置**: `backend/app/db.py`

**改造**：
- 新增 `DB_BACKEND=sqlite|postgres` 环境变量
- 默认 `sqlite`（dev 友好）
- postgres 走原 `DATABASE_URL` 路径
- Alembic migrations 兼容两套

**验证**：
- `DB_BACKEND=sqlite uvicorn app.main:app` 启动成功
- 跑 `pytest backend/tests/test_models.py` 通过
- 已有 data 迁移脚本不破坏

**风险**：
- JSON 字段类型差异（Postgres JSONB vs SQLite TEXT）
- 全文搜索功能（SQLite FTS5 vs Postgres tsvector）

**KB 参考**: aitrader-implementation-ready.md §"DB backend selection"

---

## PR-4: cache 失败不阻塞 API（半天）

> **目标**: 即使 cache 完全挂掉（redis 进程被杀），kline API 仍能返回数据。

**位置**: `backend/app/routers/kline.py:39-42`

**现状**：
```python
try:
    await cache.cache_set(key, data, ttl=300)
except Exception as e:
    logger.error(f"Cache set error: {e}")
    # 但 cache_set 现在已经 return False 不抛异常
    # 真要修的是：fetch_from_db 失败时仍要响应
```

**改造**：
1. `cache_set` 失败 → log + continue（已部分生效：降级态直接返回 False）
2. 加单元测试：`mock cache.cache_set 抛异常` → endpoint 仍 200 OK 返回数据

**验证**：
- `pytest backend/tests/test_kline_router.py -x` 通过
- 手动：杀掉 redis 进程 → `curl /api/v1/kline/BTC-USDT` 仍返回

---

## PR 顺序与依赖

```
PR-2 (follow async + ccxt 复用)
   ↓
PR-4 (cache 失败不阻塞 — 依赖 PR-2 的信号管道稳定)
   ↓
PR-3 (SQLite 适配 — 独立可插，但放最后因为需要更多测试)
```

**累计时间**: PR-2 1 天 + PR-4 半天 + PR-3 1 天 = **2.5 天**

---

## 不再需要的 PR（已 no-op）

- ~~PR-1 OBV 向量化~~ — `2258236`
- ~~PR-1 cache 降级~~ — `2258236`
- ~~PR-1 signal_service DI 改造~~ — 文件已删
- ~~PR-1 analytics 测试补全~~ — 已有 19 个测试

---

## 引用

- [SPEC v2.0](../SPEC.md) §"v2 立即可执行的技术债清单"
- [kbkkk-architect-review.md](file:///Users/hahaha/Desktop/CODE/meiduo-workspace/kb/notes/kbkkk-architect-review.md) §5（含 1 处误判）
- [vibetrading-implementation-ready.md](file:///Users/hahaha/Desktop/CODE/meiduo-workspace/kb/notes/vibetrading-implementation-ready.md) — async hook + provider registry
- [aitrader-implementation-ready.md](file:///Users/hahaha/Desktop/CODE/meiduo-workspace/kb/notes/aitrader-implementation-ready.md) — DB backend selection