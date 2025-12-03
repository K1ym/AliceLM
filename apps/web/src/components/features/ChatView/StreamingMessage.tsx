"use client"

import { Bot } from "lucide-react"
import { StreamingThinkingBlock } from "@/components/patterns/ThinkingBlock"
import { AnimatedTextWithCursor } from "@/components/ui/animated-text"

interface StreamingMessageProps {
  content: string
  reasoning?: string
}

/**
 * 流式消息组件
 * 用于展示正在生成中的 AI 回复
 */
export function StreamingMessage({
  content,
  reasoning,
}: StreamingMessageProps) {
  return (
    <div className="flex gap-3 justify-start">
      {/* AI 头像 */}
      <div className="w-8 h-8 rounded-full bg-neutral-900 flex items-center justify-center flex-shrink-0">
        <Bot size={16} className="text-white" />
      </div>

      <div className="max-w-[85%] md:max-w-[70%] space-y-2">
        {/* 思维链 */}
        {reasoning && (
          <StreamingThinkingBlock content={reasoning} />
        )}

        {/* 流式内容 */}
        {content && (
          <div className="bg-white border border-neutral-200 rounded-2xl px-4 py-3 shadow-sm">
            <AnimatedTextWithCursor
              text={content}
              delimiter=" "
              isStreaming={true}
              className="text-sm leading-relaxed text-neutral-900"
            />
          </div>
        )}

        {/* 空状态时显示加载指示 */}
        {!content && !reasoning && (
          <div className="bg-white border border-neutral-200 rounded-2xl px-4 py-3 shadow-sm">
            <div className="flex items-center gap-2 text-sm text-neutral-400">
              <span className="inline-block w-2 h-2 bg-neutral-400 rounded-full animate-pulse" />
              <span>Alice 正在思考...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
