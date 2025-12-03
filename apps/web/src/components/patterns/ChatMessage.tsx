"use client"

import { motion } from "framer-motion"
import { User, Bot } from "lucide-react"
import { cn } from "@/lib/utils"
import { ThinkingBlock } from "./ThinkingBlock"

interface ChatMessageProps {
  id: number
  role: "user" | "assistant"
  content: string
  reasoning?: string | null
  sources?: string[]
  isNew?: boolean
  className?: string
}

/**
 * 消息气泡组件
 * 遵循 DESIGN_SYSTEM.md 规范:
 * - 用户消息: bg-neutral-900 text-white, 右对齐
 * - AI消息: bg-white border-neutral-200, 左对齐
 * - 圆角: rounded-2xl (16px)
 * - 文字: text-sm (14px)
 */
export function ChatMessage({
  id,
  role,
  content,
  reasoning,
  sources,
  isNew = false,
  className,
}: ChatMessageProps) {
  const isUser = role === "user"

  return (
    <motion.div
      key={id}
      initial={isNew ? { opacity: 0, y: 16 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ 
        duration: 0.4, 
        ease: [0.25, 0.1, 0.25, 1] 
      }}
      className={cn(
        "flex gap-3",
        isUser ? "justify-end" : "justify-start",
        className
      )}
    >
      {/* AI 头像 */}
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-neutral-900 flex items-center justify-center flex-shrink-0">
          <Bot size={16} className="text-white" />
        </div>
      )}

      <div className="max-w-[85%] md:max-w-[70%] space-y-2">
        {/* 思维链 (AI 消息) */}
        {!isUser && reasoning && (
          <ThinkingBlock content={reasoning} />
        )}

        {/* 消息内容 */}
        <div
          className={cn(
            "rounded-2xl px-4 py-3",
            isUser
              ? "bg-neutral-900 text-white"
              : "bg-white border border-neutral-200 shadow-sm"
          )}
        >
          <p className="whitespace-pre-wrap text-sm leading-relaxed">
            {content}
          </p>
        </div>

        {/* 来源引用 (AI 消息) */}
        {!isUser && sources && sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {sources.map((source, i) => (
              <span
                key={i}
                className="text-xs text-neutral-400 hover:text-neutral-600 cursor-pointer transition-colors"
              >
                [{source}]
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 用户头像 */}
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-neutral-200 flex items-center justify-center flex-shrink-0">
          <User size={16} className="text-neutral-600" />
        </div>
      )}
    </motion.div>
  )
}
