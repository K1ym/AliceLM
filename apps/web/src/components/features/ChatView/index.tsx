"use client"

import { useRef, useEffect } from "react"
import { motion } from "framer-motion"
import { ChatMessage } from "@/components/patterns/ChatMessage"
import { StreamingThinkingBlock } from "@/components/patterns/ThinkingBlock"
import { StreamingMessage } from "./StreamingMessage"
import { AliceInput } from "@/components/core/AliceInput"
import type { Message, ConversationDetail } from "@/lib/api"

interface StreamingState {
  isStreaming: boolean
  content: string
  reasoning: string
  chatId: number | null
}

interface MentionContext {
  mentions?: Array<{
    type: string
    id: number
    title: string
    content?: string
  }>
  model?: string
  endpointId?: string
}

interface ChatViewProps {
  chat: ConversationDetail
  streaming: StreamingState
  onSendMessage: (value: string, context?: MentionContext) => Promise<void>
  onCancelStream: () => void
  isSending?: boolean
  parseReasoning?: (sources: string | null) => string | null
}

/**
 * 对话视图组件
 * 负责展示消息列表、流式输出、输入框
 * 遵循 DESIGN_SYSTEM.md 布局规范
 */
export function ChatView({
  chat,
  streaming,
  onSendMessage,
  onCancelStream,
  isSending = false,
  parseReasoning,
}: ChatViewProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chat.messages, streaming.content, streaming.reasoning])

  // 解析思维链
  const getReasoning = (sources: string | null): string | null => {
    if (parseReasoning) return parseReasoning(sources)
    if (!sources) return null
    try {
      const data = JSON.parse(sources)
      return data.reasoning || null
    } catch {
      return null
    }
  }

  return (
    <motion.div 
      className="h-full flex flex-col"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {/* 历史消息 */}
          {chat.messages.map((msg, index) => (
            <ChatMessage
              key={msg.id}
              id={msg.id}
              role={msg.role as "user" | "assistant"}
              content={msg.content}
              reasoning={msg.role === "assistant" ? getReasoning(msg.sources) : null}
              isNew={index === chat.messages.length - 1}
            />
          ))}

          {/* 流式输出中的内容 */}
          {streaming.isStreaming && streaming.chatId === chat.id && (
            <StreamingMessage
              content={streaming.content}
              reasoning={streaming.reasoning}
            />
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 输入框 */}
      <div className="px-6 pb-6 pt-2">
        <div className="max-w-3xl mx-auto">
          <AliceInput
            onSubmit={onSendMessage}
            onCancel={onCancelStream}
            placeholder="继续对话..."
            isStreaming={streaming.isStreaming}
            disabled={false}
          />
        </div>
      </div>
    </motion.div>
  )
}
