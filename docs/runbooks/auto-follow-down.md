# Runbook: auto-follow-worker down

## 症状

- **Prometheus**: `up{job="backend"} == 0`
- **Grafana**: "Worker Down" 红色面板
- **告警**: P3 `HealthCheckFailed`（持续 1min）或 P2/P1 业务告警

## 30 秒定位

```bash
# 1. 看容器状态
docker compose ps auto-follow-worker

# 2. 看容器日志（最近 100 行）
docker compose logs --tail=100 auto-follow-worker

# 3. 手动验证 backend 健康端点
docker compose exec backend curl -f http://localhost:8000/api/v1/health
```

## 恢复步骤

```bash
# 步骤 1：重启 worker
docker compose restart auto-follow-worker

# 步骤 2：等待健康检查（30s 内）
sleep 30

# 步骤 3：验证 Prometheus target 状态
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="backend") | .health'

# 步骤 4：确认 target UP
# 期望输出: "up"

# 步骤 5：通知 oncall Slack 频道（#incidents）
```

## 升级路径

| 重启次数 | 结果 | 动作 |
|---------|------|------|
| 1 次 | 失败 | 重启后继续监控 |
| 2 次 | 失败 | 升级到 oncall engineer |
| 3 次 | 失败 | **P1 升级**：立即通知 team lead + CTO |

## 临时降级

如果 worker 持续失败，业务上需要临时降级：

```bash
# 关闭 worker（保留 backend 和 db）
docker compose stop auto-follow-worker

# 验证依赖服务仍健康
docker compose ps
curl http://localhost:8000/api/v1/health
```

## 复盘要求

- [ ] 记录故障开始时间、恢复时间
- [ ] 5 Why 根因分析
- [ ] Action Items 入 sprint backlog
- [ ] 检查 3 次失败是否由同一根因引起（若是，必须修复才能重新启用 worker）
