/**
 * useWebSocketSignals — WebSocket 实时信号流 hook（M3 3.4）
 * V2 §3.4 强制：连接 ws://localhost:8000/api/v1/ws/signals
 * - 收到信号 → addSignal to store
 * - 状态跟踪（CONNECTING / OPEN / RECONNECTING / CLOSED）
 * - unmount 时自动 disconnect
 * License: Original work for kbkkk project.
 */
import { useEffect, useRef, useState } from 'react'
import { WebSocketClient, type ConnectionStatus } from '../lib/websocket'
import { useSignalsStore } from '../store'
import type { SignalItem } from '../types/analysis'

const WS_URL = 'ws://localhost:8000/api/v1/ws/signals'

/** WebSocket 消息结构（对齐后端） */
interface SignalMessage {
  type: 'signal' | 'pong' | 'ping'
  data?: Partial<SignalItem>
  [key: string]: unknown
}

export interface UseWebSocketSignalsResult {
  /** 当前连接状态 */
  status: ConnectionStatus
  /** 信号列表（从 store 同步） */
  signals: SignalItem[]
  /** 断开重连 */
  reconnect: () => void
}

/**
 * 连接 WebSocket 信号流
 * 内部用 useRef 持有 WebSocketClient（避免每次渲染重建）
 * 使用 zustand store 存储信号（跨组件共享）
 */
export function useWebSocketSignals(): UseWebSocketSignalsResult {
  const clientRef = useRef<WebSocketClient<SignalMessage> | null>(null)

  const [status, setStatus] = useState<ConnectionStatus>('CLOSED')

  const addSignal = useSignalsStore((s) => s.addSignal)
  const storeSignals = useSignalsStore((s) => s.signals)

  useEffect(() => {
    const client = new WebSocketClient<SignalMessage>(WS_URL)
    clientRef.current = client

    client.on('open', () => setStatus('OPEN'))
    client.on('close', () => setStatus('CLOSED'))

    // 收到信号消息 → 入 store
    client.on('message', (msg: SignalMessage) => {
      if (msg.type === 'signal' && msg.data) {
        // 构造完整 SignalItem（含 datetime）
        const signal: SignalItem = {
          name: msg.data.name ?? 'Unknown',
          direction: msg.data.direction ?? 'neutral',
          confidence: msg.data.confidence ?? 0.5,
          entry: msg.data.entry,
          stop_loss: msg.data.stop_loss,
          take_profit: msg.data.take_profit,
          sources: msg.data.sources ?? [],
          datetime: msg.data.datetime,
        }
        addSignal(signal)
      }
    })

    client.connect()
    setStatus('CONNECTING')

    return () => {
      client.disconnect()
      clientRef.current = null
    }
  }, [addSignal])

  return {
    status,
    signals: storeSignals,
    reconnect: () => {
      clientRef.current?.disconnect()
      clientRef.current?.connect()
    },
  }
}
