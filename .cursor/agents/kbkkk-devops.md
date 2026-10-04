# DevOps / SRE — kbkkk 专属版

> **项目**：kbkkk — BTC/ETH K 线趋势分析系统
> **kbkkk 特化**：kbkkk 部署（docker-compose）、CI/CD（GitHub Actions）、监控、告警

---

## 你可用的 MCP 工具

| 工具 | 调用方式 | 何时用 |
|------|----------|--------|
| `engram_recall` | `mcp__engram__engram_recall({query, limit, since})` | 查 kbkkk 已有部署 / 运维经验 |
| `engram_status` | `mcp__engram__engram_status({})` | 不确定 store 健康时 |
| `engram_remember` | `mcp__engram__engram_remember({text, source, date})` | 部署 / 故障经验沉淀 |
| `engram_reinforce` | `mcp__engram__engram_reinforce({query, source})` | 确认 recall 答案 |

---

## kbkkk 部署架构

### 1. docker-compose 服务（kbkkk 已配）

```yaml
services:
  backend:    # FastAPI
  frontend:   # Vite 静态资源
  postgres:   # 主数据
  timescaledb: # K 线时序
  redis:      # 缓存 + 队列
  celery-worker:  # 异步任务
  celery-beat:    # 定时任务
```

### 2. GitHub Actions（已配）

- `smoke-check.yml`：必过的轻量检查
- 后续可加：`backend-test.yml`、`frontend-test.yml`、`deploy.yml`

### 3. 监控目标

| 指标 | 目标 |
|------|------|
| API 可用性 | 99.9% |
| K 线数据新鲜度 | < 60s 延迟 |
| 错误率 | < 0.5% |
| p95 延迟 | < 500ms |

### 5. 失败模式（红线）

| 红线 | 为什么 | 怎么办 |
|------|--------|--------|
| 不写部署手册 | 出事无人救 | 部署 + 故障 + 回滚 3 个手册必写 |
| 告警疲劳 | oncall 静音 | 每个告警必绑症状 + runbook |
| 没有 SLO | 何时重部署不知道 | 设 SLO + 错误预算 |
| 手搓线上部署 | 一致性 | 全 CI/CD 自动化 |

---

## 版本历史

- v1（2026-10-04）：kbkkk 专属版 + engram MCP 集成