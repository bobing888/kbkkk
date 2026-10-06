/** engram chunk 数据结构（对齐 engram CLI 输出） */
export interface EngramChunk {
  /** hash(source + lines) — 唯一 id */
  id: string
  /** 原始内容（≤ 2000 字）*/
  text: string
  /** BM25 分数 0-1 */
  score: number
  /** 绝对路径 */
  source: string
  /** 行号范围 */
  lines: [number, number]
  /** ISO8601 时间戳 */
  when: string
  /** 引用格式 "path:start-end" */
  citation: string
}
