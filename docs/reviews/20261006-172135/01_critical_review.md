# 严重 Bug 审查 — useEngramRecall Hook + engram router

> **审查者**: code-reviewer (薄壳，ao-code-reviewer 角色)
> **审查对象**: backend/app/routers/engram.py + frontend/src/hooks/useEngramRecall.ts + tests
> **分支**: feature/use-engram-recall
> **日期**: 2026-10-06
> **BASE**: 70a1f94 | **HEAD**: 33dfa24 | **变更**: 4 文件 / 311 行

## CRITICAL（必须修复，0 个）

✅ 无 CRITICAL 问题

## IMPORTANT（建议本次修，2 个）

### [IMPORTANT-1] 后端 _parse_engram_output 启发式解析脆弱

**位置**: `backend/app/routers/engram.py:51-78`

**问题**:
- 启发式正则 `r'^([^\s:]+):(\d+)(?:-(\d+))?\s*(.*)$'` 假设每行有 `path:line` 格式
- engram CLI 实际输出格式未确认（**架构设计阶段就未验证**，回看架构文档 `ao-output/20261006-162929/03a_tech_design.md` 第 4 行只写"集中维护"但没说格式）
- 若 engram 输出是 JSON，启发式解析将返回乱数据；若是 Markdown，更不会匹配
- 当前 `chunks` 全部 `score=1.0`、`when=""`、`source=""` 兜底——隐藏 bug

**建议**:
```python
# 1. 立即验证 engram 实际输出格式
# 在 repo 根跑：npx @jnmetacode/engram recall "KDJ" --limit 1
# 看 stdout 长什么样，再回来改 parser

# 2. 防御性解析（按 JSON / 文本两种情况兜底）
def _parse_engram_output(raw: str) -> list[dict]:
    raw = raw.strip()
    if not raw:
        return []
    # 优先 JSON
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "chunks" in data:
            return data["chunks"]
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # 兜底：启发式（仅当 JSON 失败）
    return _heuristic_parse(raw)
```

**理由**: `systematic-debugging` 第 1 阶段"根因调查"——engram 输出格式没摸清就写 parser = 修错地方

### [IMPORTANT-2] 前端 Hook 缺 AbortController，组件卸载后 fetch 仍继续

**位置**: `frontend/src/hooks/useEngramRecall.ts:32-44`

**问题**:
- `recallChunks` 内 fetch 无 AbortController
- 组件卸载后 queryFn 仍继续（TanStack Query v5 默认行为，但 React StrictMode 下会触发双请求）
- 无超时（engram recall 慢时无降级）

**建议**:
```ts
async function recallChunks(query: string, limit: number, signal?: AbortSignal): Promise<EngramChunk[]> {
  const res = await fetch(ENGRAM_ENDPOINT, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query, limit }),
    signal,                                    // 传给 fetch
  })
  if (!res.ok) {
    throw new Error(`engram recall failed: ${res.status}`)
  }
  const json = await res.json()
  return json.chunks ?? []
}

export function useEngramRecall(query, options = {}) {
  const result = useQuery<EngramChunk[]>({
    queryKey: ['engram', 'recall', query, limit],
    queryFn: ({ signal }) => recallChunks(query, limit, signal),  // ← signal 自动提供
    // ...
  })
  // ...
}
```

**理由**: React 18 StrictMode + TanStack Query v5 标准模式

## MINOR（下次 PR 处理，4 个）

### [MINOR-1] `engram` 模块在 `model:str=''` 时可能产空 citation
第 86 行 `citation: f"{path}:{start}-{end or start}"` 当 path="" 时输出 ":1-1"。

### [MINOR-2] 测试用例缺"空 chunks 数组"分支
仅测了非空、失败、loading、enabled=false——少 1 个"成功但 chunks=[]"分支。

### [MINOR-3] `_rate_store` 字典永不清理
in-memory rate limiter 无 TTL，长时间运行内存增长。

### [MINOR-4] 前端缺 `__tests__/__snapshots__/` 防回归
其他组件（如 KLineChart）有 snapshot，本 Hook 无。

## QUESTION（需作者解释，0 个）

✅ 无 QUESTION

## 结论

| 档 | 数量 | 处理 |
|---|---|---|
| CRITICAL | 0 | — |
| IMPORTANT | 2 | **本次修**（解析稳健性 + AbortController）|
| MINOR | 4 | 下次 PR |

**处理建议**:
1. 修完 IMPORTANT-1/2 再 commit（不要 `--no-verify`）
2. MINOR 进 follow-up issue
3. 重跑全测 + lint 验证

**不修不 commit 原则** — 当前代码可运行但不够稳健，建议修完再合。
