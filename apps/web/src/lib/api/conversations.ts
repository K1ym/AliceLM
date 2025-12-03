/**
 * 对话 API
 */

import { client } from "./client"
import type { Conversation, ConversationDetail, StreamEvent } from "./types"

export const conversationsApi = {
  list: () => client.get<Conversation[]>("/conversations"),
  
  create: () => client.post<Conversation>("/conversations"),
  
  get: (id: number) => client.get<ConversationDetail>(`/conversations/${id}`),
  
  delete: (id: number) => client.delete(`/conversations/${id}`),

  /**
   * 流式发送消息
   * 
   * 注意：流式请求直接访问后端，绕过 Next.js 代理（rewrite 会缓冲响应）
   */
  sendMessageStream: async function* (
    id: number,
    content: string,
    signal?: AbortSignal
  ): AsyncGenerator<StreamEvent> {
    const token = localStorage.getItem("token")
    // 流式请求直接访问后端端口
    const streamBaseUrl = process.env.NEXT_PUBLIC_API_STREAM_URL || "http://localhost:8000"

    const response = await fetch(
      `${streamBaseUrl}/api/v1/conversations/${id}/messages/stream`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content }),
        signal,
      }
    )

    if (!response.ok) {
      yield { type: "error", error: `HTTP ${response.status}` }
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      yield { type: "error", error: "No reader available" }
      return
    }

    const decoder = new TextDecoder()
    let buffer = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6))
            yield data as StreamEvent
          } catch {
            // ignore parse errors
          }
        }
      }
    }
  },
}
