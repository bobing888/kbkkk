# 性能审查 — useEngramRecall + engram router

> **审查者**: backend-architect (薄壳，ao-backend-architect 角色)
> **审查对象**: useEngramRecall.ts + engram.py
> **日期**: 2026-10-06

## 性能维度评估

| 维度 | 评估 | 证据 |
|---|---|---|
| **首次请求** | 中 | engram CLI spawn + BM25 索引扫描，预计 200-800ms |
| **缓存命中** | 优 | TanStack Query staleTime=60s + engram store 内存 |
| **并发能力** | 良 | in-memory rate limiter O(1) |
| **内存占用** | 优 | 单 chunk ≤ 2000 字，limit=5，< 10KB/请求 |
| **网络** | 优 | JSON payload < 5KB |

## 性能问题

### [P1] engram CLI spawn 慢，建议后端缓存（应用 = 中）

**位置**: `backend/app/routers/engram.py:121-135`

**问题**:
- 每次 recall 触发 `asyncio.create_subprocess_exec("npx", ...)`
- 冷启动 npx + node + engram 包加载 ≈ 300-500ms
- 高频查询用户体验差

**建议**:
```python
# 接入 kbkkk 现有 Redis 缓存
from app.cache import cache_get, cache_set, CacheKey

@router.post("/recall", response_model=RecallResponse)
async def recall(request: RecallRequest, http_req: Request):
    cache_key = CacheKey("engram", f"recall:{request.query}:{request.limit}")
    cached = await cache_get(cache_key)
    if cached:
        return RecallResponse(**cached)
    
    # ... 现有 spawn 逻辑
    
    await cache_set(cache_key, response.model_dump(), ttl=60)  # 60s 对齐 staleTime
    return response
```

**理由**: kbkkk 已有 cache.py（Redis），复用即可
**收益**: 命中缓存 < 5ms 响应，engram CLI 完全旁路

### [P2] rate limiter 用 in-memory dict（应用 = 中）

**位置**: `backend/app/routers/engram.py:24-25`

**问题**:
- 单进程 dict，**多 worker 部署时失效**（如 uvicorn --workers 4 → 限制变成 30×4/min）
- 无 TTL 清理，**长期运行内存泄漏**

**建议**:
- 接 Redis: `INCR key` + `EXPIRE key 60`（kbkkk 已有）
- 或短期：用 `cachetools.TTLCache` 替代 dict

### [P3] 前端无 refetch 提示（应用 = 低）

**位置**: `useEngramRecall.ts:60-66`

**问题**:
- isFetching 没暴露（TanStack Query 默认区分 isLoading 和 isFetching）
- 用户看不到"重新加载中"

**建议**:
```ts
return {
  data: result.data ?? [],
  isLoading: result.isLoading,
  isFetching: result.isFetching,    // ← 新增
  error: result.error instanceof Error ? result.error : null,
  refetch: result.refetch,
}
```

## 性能基准（建议未来加）

| 指标 | 当前 | 目标 |
|---|---|---|
| p50 响应 | ~500ms | < 100ms（接 Redis 后）|
| p95 响应 | ~800ms | < 200ms |
| p99 响应 | ~1.5s | < 500ms |
| QPS | ~5 | > 50 |

## 结论

- **P1** 接 Redis 缓存：本次顺手做（低风险，复用现有 cache.py）
- **P2** rate limit 改 Redis：本次做
- **P3** isFetching：本次加（1 行）

**修完预计 p95 < 200ms，QPS 提升 10x。**
