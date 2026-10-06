# M5 部署设计：kbkkk 替换 ai-trader

> **日期**: 2026-10-06
> **版本**: v0.1（草案）
> **范围**: 服务器 `kbkkk-prod`（206.187.211.211）用 kbkkk 替换 ai-trader
> **状态**: 等用户批准
> **前置**: M0-M4 已合 main（PR #1-#17）

---

## 🎯 目标

用 kbkkk（v1.0，commit `9e0dbc4`）**完整替换**服务器上 `/opt/ai-trader` 提供的功能：

- 多市场 K 线查询（A股 / 美股 / 加密）
- 技术指标计算（6 核心 + 5 高级）
- 形态识别 + 共振信号
- 跟单引擎（auto-follow-worker）
- 公网 `kbkkk.com` 域名 HTTP 访问

**当前服务器状态**（2026-10-06 12:16 侦察）：

| 项 | 现状 |
|---|---|
| OS | Ubuntu 22.04 LTS |
| Python | 3.10.12 |
| Docker | 5.5.1 + Compose v2 |
| Nginx | 1.18.0（监听 80，公网反代）|
| ai-trader 容器 | backend(8765) + frontend(8123) + redis(6379) |
| 域名 | `kbkkk.com` `www.kbkkk.com` → `206.187.211.211` |
| 备份 | `/opt/ai-trader-backup{,2}` 已存在 |

---

## 📐 范围（与原 ai-trader 的功能对比）

| 功能 | ai-trader | kbkkk | 处理 |
|---|---|---|---|
| K 线查询 | ✅ akshare/yfinance/ccxt | ✅ cn/us/crypto 三市场 | ✅ 等价 |
| 技术指标 | ✅ 完整 17+ | ✅ 11 指标（6+5）| ✅ 等价 |
| 跟单 | ✅ strategies + trades + WS | ✅ auto-follow-worker | ✅ 等价 |
| 策略配置 | ✅ strategies CRUD | ❌ 无 | ⚠️ **缺失** |
| 用户偏好 | ✅ preferences | ❌ 无 | ⚠️ **缺失** |
| 通知 | ✅ notifications | ❌ 无 | ⚠️ **缺失** |
| WebSocket | ✅ ws_router | ❌ 无 | ⚠️ **缺失** |
| 信号 | ✅ signals + analysis | ✅ 多指标共振 | ✅ 部分 |
| 数据源 | OKX（kbkkk 区域）| ❌ **Binance 硬编码** | ❌ **必须改** |

> **数据源是阻塞点**：kbkkk `_get_crypto_kline` 写死 `ccxt.binance()`，kbkkk 区域 Binance 被屏蔽 → **必须先 PR 加 OKX 支持**才能部署。

---

## 🏗️ 架构（部署版）

```
公网 kbkkk.com:80
  ↓ Nginx (宿主机)
    ├── /api/* → 127.0.0.1:8765 → Docker kline-backend (kbkkk)
    │                              ↑ metrics 8001 / health 8002
    │                              ↓
    │                          kline-postgres (5432) + ai-trader-redis (6379, 复用)
    │                              ↑
    │                          kline-follow-worker (跟单)
    │
    └── /       → 宿主机直接 serve /opt/kbkkk-frontend/dist (Vite build)
```

---

## 🔄 部署步骤（4 阶段）

### 阶段 0：PR 改造（**先做**）

**目标**：kbkkk 支持 OKX 数据源，**PR 合 main 后才能部署**。

| 任务 | 说明 |
|---|---|
| 0.1 | TDD：写 `_get_crypto_kline` 接受 `DATA_SOURCE` env 的测试 |
| 0.2 | 实现：ccxt.binance → ccxt.okx（通过 `DATA_SOURCE` env 切换，默认 `okx`）|
| 0.3 | 测试：mock OKX API 响应，验证 symbol 转换 + 时间周期映射 |
| 0.4 | Commit + PR + CI + merge to main |

**PR 标题**：`feat(data): 支持 OKX 数据源（kbkkk 区域 Binance 被屏蔽）`

### 阶段 1：部署验证（不替换）

**目标**：并行起 kbkkk 容器，验证基础设施可用。

| 任务 | 说明 |
|---|---|
| 1.1 | 服务器 `git clone https://github.com/bobing888/kbkkk.git /opt/kbkkk` |
| 1.2 | 改 docker-compose.yml：删 redis 服务、加 ai-trader_default external network、backend 端口 `8765:8000` |
| 1.3 | 写 `.env`：`DATA_SOURCE=okx`、`REDIS_URL=redis://ai-trader-redis:6379/0` |
| 1.4 | `docker compose up -d postgres backend` |
| 1.5 | `curl http://127.0.0.1:8765/api/v1/health` → 200 |
| 1.6 | `curl http://127.0.0.1:8765/api/v1/kline/BTC/USDT?period=1d&market=crypto&limit=5` → 真实 OKX 数据 |
| 1.7 | **不替换**：ai-trader 容器继续跑，8765 端口两边竞争 → 临时改 kbkkk 端口为 `8766:8000` |

### 阶段 2：前端 + 切换（**用户拍板后才执行**）

**目标**：前端 build + 切换 Nginx 反代。

| 任务 | 说明 |
|---|---|
| 2.1 | 本地 `npm run build` → 产物 `frontend/dist/` |
| 2.2 | `rsync dist/ root@kbkkk-prod:/opt/kbkkk-frontend/dist/` |
| 2.3 | Nginx 加 `location /` → `root /opt/kbkkk-frontend/dist` + `try_files` SPA |
| 2.4 | 验证 `https://kbkkk.com` 加载前端 + API 通 |
| 2.5 | **拍板**：停 ai-trader 容器，kbkkk backend 占 8765 |

### 阶段 3：跟单 worker 启动

| 任务 | 说明 |
|---|---|
| 3.1 | `docker compose up -d auto-follow-worker` |
| 3.2 | 验证 worker 8001/metrics 200 + 8002/health 200 |
| 3.3 | 验证 postgres 迁移表完整 + redis 缓存命中 |
| 3.4 | 跑 24h 冒烟（跟单至少触发 1 次）|

---

## 📁 文件变更清单

### 服务端（kbkkk-prod）

| 路径 | 变更 |
|---|---|
| `/opt/ai-trader-backup-20261006-1216.tar.gz` | 备份 2.4M |
| `/opt/kbkkk/` | git clone（main 分支）|
| `/opt/kbkkk/docker-compose.yml` | 改：删 redis + 加 ai-trader_default + 端口 8765 |
| `/opt/kbkkk/.env` | 写：DATA_SOURCE=okx + REDIS_URL |
| `/opt/kbkkk-frontend/dist/` | scp 上传前端构建产物 |
| `/etc/nginx/sites-enabled/kbkkk` | 改：`location /` 指向 `/opt/kbkkk-frontend/dist` |

### kbkkk 仓库

| 路径 | 变更 |
|---|---|
| `backend/app/services/data_fetcher.py` | 加 `DATA_SOURCE` env 支持，crypto 默认 okx |
| `backend/tests/test_data_fetcher.py` | 加 OKX 集成测试（mock）|
| `docs/design/m5-deploy-prod.md` | 本文档 |

### ai-trader 容器

| 路径 | 变更 |
|---|---|
| `ai-trader-backend` 容器 | **保留**：等 kbkkk 验证后再停 |
| `ai-trader-frontend` 容器 | **保留**：等前端切换后再停 |
| `ai-trader-redis` 容器 | **保留**：kbkkk 复用 |
| docker volume `ai-trader_backend-data` | **保留**：strategies.db 数据 |

---

## ⚠️ 风险与缓解

| # | 风险 | 缓解 |
|---|---|---|
| 1 | OKX 公开 API 限流（公开端点 20 req/s）| Redis 缓存 K 线 + 增量对账 |
| 2 | kbkkk 功能缺（通知/WS/偏好）| 阶段 1 验证后拍板：是否真替换，还是并行 |
| 3 | ai-trader 容器数据迁移 | strategies.db 不动，ai-trader 容器保留可回滚 |
| 4 | Nginx 反代错配（公网 5xx）| 阶段 2 步骤 2.4 必须公网冒烟，不只 curl localhost |
| 5 | 端口冲突（8765 / 8123）| 阶段 1 阶段用 8766，阶段 2 切换 8765 |
| 6 | OKX PR 没合就部署 | **强制阶段 0 先完成**（PR #18 流程）|
| 7 | 服务器 docker compose build 失败（缺网络/镜像）| 阶段 1 步骤 1.4 失败立即停，回报 |

---

## 🛑 关键决策点（待用户拍板）

| # | 决策 | 选项 | 我的推荐 |
|---|---|---|---|
| 1 | OKX 改造是否独立 PR | 是 / 否 | **是**（PR #18）|
| 2 | 阶段 1 是否并行 | 是（kbkkk 8766 临时端口）| **是**（推荐，最安全）|
| 3 | ai-trader 容器何时停 | 阶段 1 验证后 / 阶段 2 切换后 / 不停 | **阶段 2 切换后** |
| 4 | strategies.db 是否迁移 | 迁移 / 不迁移 | **不迁移**（kbkkk 无 strategies 模块）|
| 5 | 域名 HTTPS 是否同步上 | 是 / 否 | **否**（用户确认仅 HTTP）|
| 6 | M4 Prometheus/Grafana | 部署 / 不部署 | **不部署**（用户确认）|

---

## 🚦 质量门禁

### 阶段 0
- [ ] OKX PR CI smoke:check 通过
- [ ] PR 合 main，commit hash 记入

### 阶段 1
- [ ] kbkkk backend `/api/v1/health` → 200
- [ ] kbkkk backend `/api/v1/kline/BTC/USDT?period=1d&market=crypto&limit=5` → 真实 OKX 数据
- [ ] postgres 表迁移成功（kline 表 + models 完整）
- [ ] redis 缓存命中（第二次请求 < 50ms）

### 阶段 2
- [ ] 公网 `http://kbkkk.com` 加载前端
- [ ] 前端能调到后端（页面显示 K 线）
- [ ] `/api/*` 全部 200
- [ ] Nginx 错误日志无 5xx

### 阶段 3
- [ ] worker 8002/health 200
- [ ] worker 8001/metrics 200
- [ ] 24h 冒烟：至少 1 次跟单信号处理
- [ ] 无内存泄漏（worker RSS < 200M）

---

## 📅 预计工期

| 阶段 | 工时 | 累计 |
|---|---|---|
| 阶段 0（PR OKX） | 1-2h | 1-2h |
| 阶段 1（部署验证） | 1h | 2-3h |
| 阶段 2（前端+切换） | 1h | 3-4h |
| 阶段 3（worker 冒烟） | 1h + 24h 等待 | 4-5h + 1d |
| 缓冲 | 1h | 5-6h + 1d |

---

## ❓ 等待批准

- [ ] 整体设计是否通过？
- [ ] 4 阶段拆解（PR→验证→切换→冒烟）是否合理？
- [ ] 6 个关键决策点是否有要改的？
- [ ] 5-6h + 24h 冒烟工期是否接受？
- [ ] **功能缺失**（通知/WS/偏好）是否确认可接受？
- [ ] **strategies.db** 是否确认不迁移？

批准后调 writing-plans skill 生成 4 阶段实施计划 + engram 沉淀决策。

---

**维护者**: kline-pm
**下次更新**: 批准后生成 writing-plans 输出
