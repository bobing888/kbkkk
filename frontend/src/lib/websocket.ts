/**
 * WebSocket Client — M3 3.4
 * V2 §3.4 强制：
 * - 指数退避重连（1s → 2s → 4s → 8s → 16s → 30s 上限）
 * - 30s 心跳 ping/pong
 * - 状态机：CONNECTING / OPEN / CLOSING / CLOSED / RECONNECTING
 * - JSON 消息解析 + 二进制支持
 * License: Original work for kbkkk project.
 */

/** WebSocket 连接状态 */
export type ConnectionStatus =
  | 'CONNECTING'
  | 'OPEN'
  | 'CLOSING'
  | 'CLOSED'
  | 'RECONNECTING'

type EventName = 'open' | 'close' | 'error' | 'message' | 'pong'

/**
 * 轻量级 WebSocket 客户端封装
 * - 自动重连（指数退避，上限 30s，最多 5 次）
 * - 30s 心跳 ping
 * - JSON / 二进制自动解析
 */
export class WebSocketClient<T = unknown> {
  private ws: WebSocket | null = null
  private url: string
  private handlers: Map<EventName, Set<(data: T) => void>> = new Map()
  private status: ConnectionStatus = 'CLOSED'
  private reconnectCount = 0
  private maxRetries = 5
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private destroyed = false

  // 指数退避基数（毫秒）
  private backoffMs = 1000
  private maxBackoffMs = 30000

  constructor(url: string) {
    this.url = url
  }

  /** 获取当前连接状态 */
  getStatus(): ConnectionStatus {
    return this.status
  }

  /** 获取重试次数 */
  getReconnectCount(): number {
    return this.reconnectCount
  }

  /** 连接到 WebSocket 服务 */
  connect(): void {
    if (this.destroyed) return

    this.status = 'CONNECTING'
    this._clearHeartbeat()

    try {
      this.ws = new WebSocket(this.url)
    } catch {
      this.status = 'CLOSED'
      this._scheduleReconnect()
      return
    }

    this.ws.addEventListener('open', () => {
      this.status = 'OPEN'
      this.reconnectCount = 0 // 重置重试计数
      this._startHeartbeat()
      this._emit('open', undefined)
    })

    this.ws.addEventListener('close', () => {
      this._clearHeartbeat()
      if (!this.destroyed) {
        this.status = 'RECONNECTING'
        this._emit('close', undefined)
        this._scheduleReconnect()
      } else {
        this.status = 'CLOSED'
        this._emit('close', undefined)
      }
    })

    this.ws.addEventListener('error', () => {
      // error 事件后会自动触发 close，故在 close 里处理重连
      this._emit('error', undefined)
    })

    this.ws.addEventListener('message', (event: MessageEvent) => {
      const data = this._parseMessage(event.data)
      if (data !== null) {
        this._emit('message', data as T)
      }
    })
  }

  /** 主动断开连接 */
  disconnect(): void {
    this._cleanup()
    this.status = 'CLOSED'
  }

  /** 发送消息 */
  send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(typeof data === 'string' ? data : JSON.stringify(data))
    }
  }

  /** 订阅事件 */
  on(event: EventName, handler: (data: T) => void): void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set())
    }
    this.handlers.get(event)!.add(handler)
  }

  /** 取消订阅 */
  off(event: EventName, handler: (data: T) => void): void {
    this.handlers.get(event)?.delete(handler)
  }

  // ─── Private ───────────────────────────────────────────────────────────────

  /** 解析消息（JSON 或二进制） */
  private _parseMessage(data: unknown): unknown {
    if (typeof data === 'string') {
      try {
        return JSON.parse(data)
      } catch {
        return data // 非 JSON 原文
      }
    }
    if (data instanceof ArrayBuffer) {
      // 尝试用 TextDecoder 解码
      try {
        const decoder = new TextDecoder()
        const str = decoder.decode(data)
        return JSON.parse(str)
      } catch {
        return { __binary: data }
      }
    }
    return data
  }

  /** 触发事件 */
  private _emit(event: EventName, data: unknown): void {
    this.handlers.get(event)?.forEach((cb) => cb(data as T))
  }

  /** 启动心跳（每 30s 发一次 ping） */
  private _startHeartbeat(): void {
    this._clearHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30_000)
  }

  /** 清除心跳定时器 */
  private _clearHeartbeat(): void {
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /** 调度重连（指数退避） */
  private _scheduleReconnect(): void {
    if (this.destroyed) return

    if (this.reconnectCount >= this.maxRetries) {
      this.status = 'CLOSED'
      return
    }

    const delay = Math.min(this.backoffMs, this.maxBackoffMs)
    this.backoffMs = Math.min(this.backoffMs * 2, this.maxBackoffMs)
    this.reconnectCount++

    this.reconnectTimer = setTimeout(() => {
      if (!this.destroyed) {
        this.connect()
      }
    }, delay)
  }

  /** 清理所有定时器和 WebSocket */
  private _cleanup(): void {
    this._clearHeartbeat()
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}
