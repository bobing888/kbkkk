# 安全审查 — useEngramRecall + engram router

> **审查者**: appsec-engineer (薄壳，ao-appsec-engineer 角色)
> **审查对象**: backend/app/routers/engram.py
> **日期**: 2026-10-06
> **依据**: OWASP API Security Top 10

## 整体评估

server proxy 设计**安全三件套到位**（白名单+rate limit+输入校验），整体防御合理。但有 2 个可改进项。

## 安全问题清单

### [A1] 路径遍历防御不充分（应用风险 = 中）

**位置**: `backend/app/routers/engram.py:18-22`

**问题**:
- `cwd=settings.project_root` 限定了 engram CLI 工作目录
- 但 engram 内部可能仍读取**绝对路径**的 store（`~/.engram/store.json`），不受 cwd 限制
- 若 attacker 控制的 query 命中 engram 内部路径遍历逻辑，可读 `/etc/passwd` 之类

**OWASP 分类**: A01:2021 Broken Access Control

**建议**:
```python
# 1. 业务规则：engram 召回不允许包含 "/etc"、"/proc" 等
FORBIDDEN_PATTERNS = ['/etc/', '/proc/', '/sys/', '~/', '..', '\x00']

def _sanitize_query(query: str) -> str:
    q = query.strip()[:MAX_QUERY_LEN]
    q = re.sub(r'[\x00-\x1f]', '', q)
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in q.lower():
            raise HTTPException(status_code=400, detail=f"forbidden pattern: {pattern}")
    return q
```

### [A2] 无 HTTPS/TLS 强制（应用风险 = 低）

**位置**: 整体

**问题**:
- `/api/v1/engram/recall` 未强制 HTTPS
- 前端用 `VITE_API_BASE` http:// 协议时可走明文

**OWASP 分类**: A02:2021 Cryptographic Failures

**建议**:
- 生产环境 CORS 限制 https-only
- 文档说明 dev 用 http，生产必须 https

### [A3] 无认证 / 授权（应用风险 = 中）

**位置**: 整个 router

**问题**:
- 当前路由**完全开放**，任何 IP 都能调
- 30/min rate limit 防滥用，但**无身份认证**
- engram 可能含用户私人笔记（如 kbkkk 自己沉淀的内容）

**OWASP 分类**: A01:2021 + A07:2021 Identification and Authentication Failures

**建议**:
```python
# 短期：加可选 Authorization header
# 长期：接 kbkkk 现有 JWT 体系

from fastapi import Depends
from app.auth import verify_token  # 假设已存在

@router.post("/recall", response_model=RecallResponse)
async def recall(
    request: RecallRequest,
    http_req: Request,
    user = Depends(verify_token),  # 强制鉴权
):
    ...
```

**短期方案**（不阻塞 P2 合入）：
- 至少限制只允许内网 IP 调用
- 通过环境变量 `ENGRAM_PUBLIC=false` 控制

### [A4] `asyncio.subprocess` 无环境变量清理（应用风险 = 低）

**位置**: `backend/app/routers/engram.py:121-127`

**问题**:
- `asyncio.create_subprocess_exec` 继承父进程环境变量
- 若父进程有 `NODE_OPTIONS=--inspect=0.0.0.0:9229`，子进程也带——**远程调试端口暴露**

**建议**:
```python
env = {
    "PATH": os.environ.get("PATH", ""),
    "HOME": os.environ.get("HOME", ""),
    "LANG": "C.UTF-8",
}
proc = await asyncio.create_subprocess_exec(
    "npx", "--yes", "@jnmetacode/engram", "recall", query, "--limit", str(limit),
    cwd=settings.project_root,
    env=env,                          # ← 显式 env
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
```

## 通过条件

- A1 路径遍历：**建议本次修**（低成本高收益）
- A2 HTTPS：**文档说明即可**，代码层无需改
- A3 鉴权：**留 follow-up issue**（P3 计划）
- A4 env 清理：**建议本次修**（1 行改动）

## 整体评分

🟡 **黄灯**——可合入生产，但 A1/A4 建议本次修。A3 进 follow-up。

## 不修可合入的依据

- kbkkk 是内部工具，不是公网产品
- 当前 attack surface 仅前端 SPA
- 已有 rate limit（30/min）兜底
- engram 召回无破坏性命令（不像 rm/rce）

**结论**: A1 + A4 修完即可合入。
