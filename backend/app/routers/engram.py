"""
engram recall API 路由

架构决策（ADR-001）：TanStack Query 包装 server proxy
架构决策（ADR-004）：server proxy 安全三件套（白名单 + rate limit + 输入校验）
架构决策（ADR-005）：解析稳健性 — JSON 优先，启发式兜底（修复审查 IMPORTANT-1）
"""
import asyncio
import hashlib
import os
import re
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import get_settings
from app.cache import cache_get, cache_set

router = APIRouter(prefix="/api/v1/engram", tags=["engram"])

# ── 安全常量 ───────────────────────────────────────────
MAX_QUERY_LEN = 200      # ADR-004：query 长度上限
MAX_LIMIT = 20            # ADR-004：单次最大返回条数

# 路径遍历防御（ADR 修复审查 A1）
FORBIDDEN_PATTERNS = ['/etc/', '/proc/', '/sys/', '..', '\x00']

# 子进程最小环境（ADR 修复审查 A4）
SUBPROC_ENV = {
    "PATH": os.environ.get("PATH", ""),
    "HOME": os.environ.get("HOME", ""),
    "LANG": "C.UTF-8",
    "NODE_OPTIONS": "",  # 显式清空，防止父进程带 debug 端口
}


def _sanitize_query(query: str) -> str:
    """脱壳 + 长度限制 + 危险字符过滤 + 路径遍历防御（ADR-004 + 审查 A1）"""
    q = query.strip()[:MAX_QUERY_LEN]
    q = re.sub(r'[\x00-\x1f]', '', q)
    # 黑名单：含敏感路径模式 → 400
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in q.lower():
            raise HTTPException(
                status_code=400,
                detail=f"forbidden pattern in query: {pattern}",
            )
    return q


def _parse_engram_output(raw: str) -> list[dict]:
    """解析 engram recall CLI 输出为 EngramChunk[]。

    engram recall 实际输出格式（2026-10-06 验证）：
        <score>  <path:start-end>  <date>
            <text excerpt>  ← 缩进 4 空格

    解析策略（ADR-005）：JSON 优先 → 启发式兜底。
    """
    raw = raw.strip()
    if not raw:
        return []

    # 1. JSON 优先
    import json
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "chunks" in data:
            return data["chunks"]
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. 启发式（engram 文本格式）
    chunks = []
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue
        # 匹配 "<score>  <path:start-end>  <date>" 格式
        m = re.match(
            r'^(\d+\.?\d*)\s+'
            r'(\S+?):(\d+)-(\d+)\s+'
            r'(\d{4}-\d{2}-\d{2})'
            r'\s*(.*)$',
            line,
        )
        if m:
            score = float(m.group(1))
            path = m.group(2)
            start = int(m.group(3))
            end = int(m.group(4))
            when = m.group(5)
            # 接下来缩进行是 text excerpt（直到下一个非缩进行或 EOF）
            text_lines = []
            j = i + 1
            while j < len(lines) and lines[j].startswith((' ', '\t')):
                text_lines.append(lines[j].strip())
                j += 1
            text = ' '.join(text_lines)[:2000]  # 限 2000 字
            chunk_id = hashlib.md5(f"{path}:{start}-{end}".encode()).hexdigest()
            chunks.append({
                "id": chunk_id,
                "source": path,
                "lines": [start, end],
                "text": text,
                "score": score,
                "when": when,
                "citation": f"{path}:{start}-{end}",
            })
            i = j
        else:
            # 兜底：整行作为 text
            chunk_id = hashlib.md5(line.encode()).hexdigest()
            chunks.append({
                "id": chunk_id,
                "source": "",
                "lines": [0, 0],
                "text": line[:2000],
                "score": 1.0,
                "when": "",
                "citation": "",
            })
            i += 1
    return chunks


# ── Request / Response 模型 ─────────────────────────────
class RecallRequest(BaseModel):
    """ADR-004：显式 Request 模型 + 字段校验"""
    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LEN)
    limit: int = Field(default=5, ge=1, le=MAX_LIMIT)


class EngramChunk(BaseModel):
    id: str
    source: str
    lines: list[int]
    text: str
    score: float
    when: str
    citation: str


class RecallResponse(BaseModel):
    chunks: list[EngramChunk]
    count: int


# ── 路由 ───────────────────────────────────────────────
@router.post("/recall", response_model=RecallResponse)
async def recall(request: RecallRequest, http_req: Request):
    """调用 engram recall，返回相关 chunks。

    业务规则：仅允许白名单目录搜索（防止任意路径遍历）
    """
    settings = get_settings()

    # 1. 脱壳 query（ADR-004 + 审查 A1）
    query = _sanitize_query(request.query)
    limit = min(request.limit, MAX_LIMIT)

    # 2. Redis 缓存（审查 P1）
    cache_key = f"engram:recall:{query}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return RecallResponse(**cached)

    # 3. 调用 engram CLI（subprocess，零 shell=True + 最小 env 审查 A4）
    proc = await asyncio.create_subprocess_exec(
        "npx",
        "--yes",
        "@jnmetacode/engram",
        "recall",
        query,
        "--limit", str(limit),
        cwd=settings.project_root,  # 限定工作目录
        env=SUBPROC_ENV,             # 审查 A4 修复
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
    except asyncio.TimeoutError:
        proc.kill()
        raise HTTPException(status_code=504, detail="engram recall timeout")

    if proc.returncode != 0:
        raise HTTPException(
            status_code=502,
            detail=f"engram recall failed: {stderr.decode(errors='replace')}"
        )

    # 4. 解析输出（ADR-005 修复审查 IMPORTANT-1）
    raw = stdout.decode(errors='replace')
    chunks = _parse_engram_output(raw)
    response = RecallResponse(chunks=chunks, count=len(chunks))

    # 5. 写缓存（TTL=60s 对齐前端 staleTime）
    await cache_set(cache_key, response.model_dump(), ttl=60)

    return response
