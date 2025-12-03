"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Brain, ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"

interface ThinkingBlockProps {
  content: string
  isStreaming?: boolean
  defaultExpanded?: boolean
  className?: string
}

/**
 * 思维链展示组件
 * 遵循 DESIGN_SYSTEM.md 规范:
 * - 背景: bg-amber-50
 * - 边框: border-amber-200
 * - 圆角: rounded-xl (12px)
 * - 呼吸动画: 流式输出时图标脉动
 */
export function ThinkingBlock({
  content,
  isStreaming = false,
  defaultExpanded = false,
  className,
}: ThinkingBlockProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <div 
      className={cn(
        "bg-amber-50 border border-amber-200 rounded-xl overflow-hidden",
        className
      )}
    >
      {/* 标题栏 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-amber-700 hover:bg-amber-100 transition-colors"
      >
        <Brain 
          size={14} 
          className={cn(isStreaming && "animate-pulse")} 
        />
        <span>{isStreaming ? "思考中..." : "思维过程"}</span>
        <span className="flex-1" />
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {/* 内容区域 */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
          >
            <div className="px-3 pb-3 text-xs text-amber-800 whitespace-pre-wrap max-h-48 overflow-y-auto">
              {content}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/**
 * 流式思维链组件 (正在生成时使用)
 */
export function StreamingThinkingBlock({
  content,
  className,
}: {
  content: string
  className?: string
}) {
  return (
    <div 
      className={cn(
        "bg-amber-50 border border-amber-200 rounded-xl overflow-hidden",
        className
      )}
    >
      <div className="flex items-center gap-2 px-3 py-2 text-xs text-amber-700">
        <Brain size={14} className="animate-pulse" />
        <span>思考中...</span>
      </div>
      <div className="px-3 pb-3 text-xs text-amber-800 whitespace-pre-wrap max-h-48 overflow-y-auto">
        {content}
      </div>
    </div>
  )
}
