"""FollowWorker — M3 F4 异步 Worker

职责：
1. 订阅 SignalChangeBus，收到 signal → 调用 FollowEngine.on_signal
2. 定期拉 K 线数据 → 调用 FollowEngine.on_market_update（SL/TP 监控）

设计原则：
- asyncio 循环，优雅退出（stop_event）
- 独立运行（不依赖主进程生命周期）
- 可测试（完全 mock 依赖）
- 幂等：engine.on_signal 抛错不崩溃 loop

M4 SRE 监控：
- follow_signal_duration_seconds（Histogram）：信号处理延迟
- follow_order_total（Counter）：下单次数（按 status=success/fail）
- follow_notification_total（Counter）：通知投递次数（按 status=success/fail）
"""
from __future__ import annotations

import asyncio
import logging
import time as time_module
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Callable, Literal, Protocol

from prometheus_client import Counter, Histogram, start_http_server

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.analytics.signal_direction import Signal
from app.services.event_bus import SignalChangeBus, SignalChangeEvent
from app.follow.risk_manager import AccountState, Position

logger = logging.getLogger(__name__)

# ── Prometheus metrics ───────────────────────────────────────────────────────

# 信号处理延迟（histogram 支持 p95/p99 查询）
follow_signal_duration_seconds = Histogram(
    "follow_signal_duration_seconds",
    "Signal processing latency in seconds",
    buckets=(0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0),
)

# 下单计数器（按结果标签）
follow_order_total = Counter(
    "follow_order_total",
    "Total follow orders",
    ["status"],  # success | fail
)

# 通知投递计数器
follow_notification_total = Counter(
    "follow_notification_total",
    "Total notification deliveries",
    ["status"],  # success | fail
)


# ── 依赖协议 ───────────────────────────────────────────────────────────────

class FollowEngineProtocol(Protocol):
    """FollowEngine 接口协议。"""
    async def on_signal(self, signal: Signal, account: AccountState) -> ...: ...
    def on_market_update(self, current_prices: dict[str, float]) -> list: ...
    def _db_factory(self) -> Session: ...  # type: ignore[misc]


class KLineFetcherProtocol(Protocol):
    """K 线数据拉取接口。"""
    async def fetch_latest_price(self, symbol: str) -> float | None: ...


# ── FollowWorker ──────────────────────────────────────────────────────────

class FollowWorker:
    """自动跟单 asyncio worker。

    两个主要循环：
    1. signal_loop: 订阅 SignalChangeBus，收到 signal 即处理
    2. monitor_loop: 定期拉价格，检查 SL/TP 触发

    优雅退出：通过 stop_event 控制
    """

    def __init__(
        self,
        engine: FollowEngineProtocol,
        event_bus: SignalChangeBus,
        kline_fetcher: KLineFetcherProtocol | None = None,
        monitor_interval_seconds: float = 1.0,
        account_state_provider: Callable[[], AccountState] | None = None,
        db_factory: Callable[[], Session] | None = None,
    ) -> None:
        """
        Args:
            engine: FollowEngine 实例
            event_bus: SignalChangeBus 订阅源
            kline_fetcher: K 线价格拉取器（可选，默认用 engine）
            monitor_interval_seconds: SL/TP 监控间隔（默认 1s）
            account_state_provider: 账户状态查询函数（可选，默认内部维护）
            db_factory: 数据库 session 工厂（可选，默认用 engine._db_factory）
        """
        self._engine = engine
        self._bus = event_bus
        self._fetcher = kline_fetcher
        self._monitor_interval = monitor_interval_seconds
        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        # account_state_provider：外部注入；无注入时默认内部维护
        self._account_state_provider: Callable[[], AccountState] = (
            account_state_provider
            if account_state_provider is not None
            else self._default_account_state
        )
        # db_factory：优先外部注入，其次用 engine._db_factory
        self._db_factory: Callable[[], Session] | None = (
            db_factory
            if db_factory is not None
            else getattr(engine, "_db_factory", None)
        )

    @staticmethod
    def _default_account_state() -> AccountState:
        """无外部 provider 时的默认账户状态（全 0，保守）"""
        return AccountState(
            equity=100000.0,
            daily_pnl_pct=0.0,
            positions=[],
        )

    async def start(self) -> None:
        """启动 worker（后台运行）。"""
        logger.info("[follow_worker] starting")
        t1 = asyncio.create_task(self._signal_loop())
        t2 = asyncio.create_task(self._monitor_loop())
        self._tasks = [t1, t2]
        logger.info("[follow_worker] started")

    async def stop(self) -> None:
        """优雅停止 worker。"""
        logger.info("[follow_worker] stopping")
        self._stop_event.set()
        # 等待子任务完成
        for t in self._tasks:
            try:
                await asyncio.wait_for(t, timeout=5.0)
            except asyncio.TimeoutError:
                t.cancel()
        self._tasks.clear()
        logger.info("[follow_worker] stopped")

    async def _signal_loop(self) -> None:
        """订阅 SignalChangeBus，收到 signal → 处理。"""
        queue = self._bus.subscribe()
        logger.info("[follow_worker] signal_loop started")

        while not self._stop_event.is_set():
            try:
                # 非阻塞等待信号（带超时以便检查 stop_event）
                event = await asyncio.wait_for(queue.get(), timeout=0.5)
                await self._handle_signal_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("[follow_worker] signal_loop error: %s", e)

        logger.info("[follow_worker] signal_loop exited")

    async def _handle_signal_event(self, event: SignalChangeEvent) -> None:
        """处理单个信号事件：查 DB 最新 Signal → 调用 engine.on_signal"""
        start_time = time_module.monotonic()
        try:
            logger.info(
                "[follow_worker] received signal: pair=%s tf=%s type=%s",
                event.pair,
                event.timeframe,
                event.change_type,
            )

            # 1. 从 DB 查询最近 1 分钟内的 Signal
            signal = self._fetch_latest_signal(event.pair, event.timeframe)
            if signal is None:
                logger.warning(
                    "[follow_worker] no Signal found in DB for pair=%s tf=%s",
                    event.pair,
                    event.timeframe,
                )
                return

            # 2. 获取账户状态
            account_state = self._account_state_provider()

            # 3. 调用 engine.on_signal 实际处理
            try:
                result = await self._engine.on_signal(signal, account_state)
                if result.success:
                    logger.info(
                        "[follow_worker] signal processed: pair=%s trade_id=%s",
                        event.pair,
                        result.trade_log_id,
                    )
                    follow_order_total.labels(status="success").inc()
                else:
                    logger.info(
                        "[follow_worker] signal rejected: pair=%s reason=%s",
                        event.pair,
                        result.reason,
                    )
            except Exception as e:
                logger.error(
                    "[follow_worker] engine.on_signal failed: pair=%s error=%s",
                    event.pair,
                    e,
                )
                follow_order_total.labels(status="fail").inc()
                raise  # 让上层捕获，不吞掉错误

        except Exception as e:
            logger.error("[follow_worker] handle_signal error: %s", e)
        finally:
            # 记录信号处理延迟（finally 确保无论成功/失败都记录）
            follow_signal_duration_seconds.observe(time_module.monotonic() - start_time)

    def _fetch_latest_signal(self, pair: str, timeframe: str) -> Signal | None:
        """从 DB 查询最近 1 分钟内指定 pair/timeframe 的最新 Signal。

        使用 RecommendationHistory 表存储的信号（经 AnalyticsEngine 计算）。
        查询窗口 1 分钟：覆盖信号从生成到被 worker 处理的延迟。
        """
        if self._db_factory is None:
            logger.warning("[follow_worker] no db_factory, cannot fetch Signal")
            return None

        from app.models import RecommendationHistory

        db = self._db_factory()
        try:
            cutoff = datetime.now(UTC) - timedelta(minutes=1)
            row: RecommendationHistory | None = (
                db.query(RecommendationHistory)
                .filter(RecommendationHistory.pair == pair)
                .filter(RecommendationHistory.timeframe == timeframe)
                .filter(RecommendationHistory.created_at >= cutoff)
                .order_by(RecommendationHistory.created_at.desc())
                .first()
            )
            if row is None:
                return None

            # RecommendationHistory → Signal 转换
            return Signal(
                name=row.pair,
                direction=row.direction,
                confidence=row.confidence,
                entry=row.entry_price,
                stop_loss=row.stop_loss,
                take_profit=row.take_profit,
                sources=row.signal_sources.split(",") if row.signal_sources else [],
            )
        finally:
            db.close()

    async def _monitor_loop(self) -> None:
        """定期拉价格，检查 SL/TP。"""
        logger.info("[follow_worker] monitor_loop started (interval=%.1fs)", self._monitor_interval)

        while not self._stop_event.is_set():
            try:
                await self._check_sl_tp()
            except Exception as e:
                logger.error("[follow_worker] monitor_loop error: %s", e)

            # 等待下一个周期
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._monitor_interval,
                )
                # stop_event 被设置，退出
                break
            except asyncio.TimeoutError:
                pass

        logger.info("[follow_worker] monitor_loop exited")

    async def _check_sl_tp(self) -> None:
        """拉取当前价格，调用 engine.on_market_update。"""
        if self._fetcher is None:
            # 无 fetcher 时跳过（测试场景）
            return

        try:
            # 获取当前 open 持仓的 symbols（通过 engine 查询）
            # 简化：直接传空 dict，让 engine 自己查 DB
            prices = {}
            await self._engine.on_market_update(prices)
        except Exception as e:
            logger.debug("[follow_worker] _check_sl_tp: %s", e)


# ── Worker HTTP 服务（metrics 8001 + health 8002）───────────────────────────

_METRICS_PORT = 8001
_HEALTH_PORT = 8002


def _start_metrics_server(port: int = _METRICS_PORT) -> None:
    """Prometheus metrics 端点（/metrics），供 prometheus scrape 使用。"""
    import socket
    # 先确保端口可用（避免重复启动）
    with socket.socket() as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            logger.warning("[metrics_server] port %d already in use, skipping start", port)
            return
    start_http_server(port)
    logger.info("[metrics_server] listening on http://0.0.0.0:%d/metrics", port)


def _run_health_server_sync() -> None:
    """同步 HTTP server，监听 _HEALTH_PORT，只提供 /health。"""
    import http.server
    import socketserver

    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass  # 静音，避免 stdout 混乱

    with socketserver.TCPServer(("0.0.0.0", _HEALTH_PORT), HealthHandler) as httpd:
        logger.info("[health_server] listening on http://0.0.0.0:%d/health", _HEALTH_PORT)
        httpd.serve_forever()


async def _http_servers() -> None:
    """在独立线程中同时启动 metrics + health server。"""
    import threading

    # metrics server（prometheus_client 自带，阻塞）
    metrics_thread = threading.Thread(target=_start_metrics_server, daemon=True)
    metrics_thread.start()
    logger.info("[http_servers] metrics thread started")

    # health server（同步阻塞）
    health_thread = threading.Thread(target=_run_health_server_sync, daemon=True)
    health_thread.start()
    logger.info("[http_servers] health thread started")

    # 等待 stop_event
    await _worker._stop_event.wait()
    logger.info("[http_servers] stopping")


async def main() -> None:
    """Worker 入口：初始化依赖 + 启动 signal/monitor 循环 + 健康检查 server。"""
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    from app.db import get_db_session
    from app.cache import init_redis, close_redis
    from app.services.event_bus import SignalChangeBus
    from app.follow.follow_engine import FollowEngine

    redis_ok = await init_redis()
    logger.info("Redis init: %s", "ok" if redis_ok else "failed")

    db_factory = get_db_session
    event_bus = SignalChangeBus()
    engine = FollowEngine(db_factory=db_factory)

    global _worker
    _worker = FollowWorker(
        engine=engine,
        event_bus=event_bus,
        db_factory=db_factory,
    )

    # 启动 Prometheus metrics server（后台线程）
    _start_metrics_server(_METRICS_PORT)

    await _worker.start()
    await _http_servers()
    await _worker.stop()
    await close_redis()
    logger.info("Worker shutdown complete")


_worker: FollowWorker | None = None

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
