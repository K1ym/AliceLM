"use client"

import { useState, useEffect, useMemo, useRef } from "react"
import {
  IconArrowUp,
  IconAt,
  IconPaperclip,
  IconX,
  IconVideo,
  IconMessage,
  IconChevronDown,
  IconPlayerStop,
} from "@tabler/icons-react"

import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useMentions, MentionItem } from "@/hooks"
import { configApi, videosApi, Video, ConfigResponse } from "@/lib/api"
import type { Conversation } from "@/lib/api"

interface AliceInputProps {
  onSubmit: (
    value: string, 
    context?: { 
      mentions: MentionItem[]
      model?: string
      endpointId?: string 
    }
  ) => void
  onCancel?: () => void // 取消流式输出
  placeholder?: string
  disabled?: boolean
  isStreaming?: boolean // 是否正在流式输出
  className?: string
  conversations?: Conversation[]
}

export function AliceInput({
  onSubmit,
  onCancel,
  placeholder = "输入问题，或粘贴视频链接...",
  disabled = false,
  isStreaming = false,
  className = "",
  conversations = [],
}: AliceInputProps) {
  const [value, setValue] = useState("")
  const [mentionPopoverOpen, setMentionPopoverOpen] = useState(false)
  const [modelMenuOpen, setModelMenuOpen] = useState(false)
  const [mentionPosition, setMentionPosition] = useState<{ top: number; left: number } | null>(null)
  const [mentionSearch, setMentionSearch] = useState("") // @ 后面输入的搜索词
  const [mentionAtIndex, setMentionAtIndex] = useState(-1) // @ 符号在文本中的位置
  
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const formRef = useRef<HTMLFormElement>(null)
  
  // 配置状态
  const [config, setConfig] = useState<ConfigResponse | null>(null)
  const [videos, setVideos] = useState<Video[]>([])
  const [selectedModel, setSelectedModel] = useState<{ endpointId?: string; model: string } | null>(null)

  // 使用 useMentions hook 管理引用逻辑
  const {
    mentions,
    filteredItems,
    addMention: hookAddMention,
    removeMention,
    clearMentions,
    setSearchText,
  } = useMentions({ videos, conversations })

  // 加载配置和视频列表
  useEffect(() => {
    async function loadData() {
      try {
        const [configRes, videosRes] = await Promise.all([
          configApi.get(),
          videosApi.list({ page_size: 50 }),
        ])
        
        if (configRes.data) {
          setConfig(configRes.data)
          const chatConfig = configRes.data.model_tasks?.chat
          if (chatConfig?.model) {
            setSelectedModel({
              endpointId: chatConfig.endpoint_id,
              model: chatConfig.model,
            })
          }
        }
        if (videosRes.data?.items) {
          setVideos(videosRes.data.items)
        }
      } catch (err) {
        console.error("[AliceInput] loadData error:", err)
      }
    }
    loadData()
  }, [])

  // 同步搜索词到 hook
  useEffect(() => {
    setSearchText(mentionSearch)
  }, [mentionSearch, setSearchText])

  // 按类型分组过滤后的项
  const groupedMentions = useMemo(() => {
    return {
      video: filteredItems.filter((item) => item.type === "video"),
      conversation: filteredItems.filter((item) => item.type === "conversation"),
    }
  }, [filteredItems])
  
  // 获取第一个匹配项（用于回车选择）
  const firstMatchedItem = useMemo(() => {
    if (groupedMentions.video.length > 0) return groupedMentions.video[0]
    if (groupedMentions.conversation.length > 0) return groupedMentions.conversation[0]
    return null
  }, [groupedMentions])

  // 获取可用模型列表
  const availableModels = useMemo(() => {
    if (!config?.llm_endpoints) return []
    
    const models: { endpointId: string; endpointName: string; model: string }[] = []
    config.llm_endpoints.forEach((endpoint) => {
      // 只获取 chat 类型的模型
      const chatModels = endpoint.models_with_type?.filter((m) => m.type === "chat") || []
      chatModels.forEach((m) => {
        models.push({
          endpointId: endpoint.id,
          endpointName: endpoint.name,
          model: m.id,
        })
      })
      // 如果没有类型信息，显示所有模型
      if (chatModels.length === 0 && endpoint.models) {
        endpoint.models.forEach((model) => {
          models.push({
            endpointId: endpoint.id,
            endpointName: endpoint.name,
            model,
          })
        })
      }
    })
    return models
  }, [config])

  // 当前选中的模型显示名称
  const selectedModelDisplay = useMemo(() => {
    if (!selectedModel) return "自动"
    const found = availableModels.find(
      (m) => m.endpointId === selectedModel.endpointId && m.model === selectedModel.model
    )
    if (found) {
      // 简化显示：只显示模型名
      const shortName = found.model.split("/").pop() || found.model
      return shortName.length > 20 ? shortName.slice(0, 20) + "..." : shortName
    }
    return selectedModel.model || "自动"
  }, [selectedModel, availableModels])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (value.trim() && !disabled) {
      onSubmit(value, {
        mentions,
        model: selectedModel?.model,
        endpointId: selectedModel?.endpointId,
      })
      setValue("")
      clearMentions()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Escape 关闭弹窗
    if (e.key === "Escape" && mentionPopoverOpen) {
      e.preventDefault()
      setMentionPopoverOpen(false)
      setMentionSearch("")
      return
    }
    
    // 弹窗打开时，回车选择第一个匹配项
    if (e.key === "Enter" && mentionPopoverOpen && firstMatchedItem) {
      e.preventDefault()
      selectMention(firstMatchedItem)
      return
    }
    
    // Enter 发送（非 shift，弹窗未打开，非 streaming）
    if (e.key === "Enter" && !e.shiftKey && !mentionPopoverOpen && !isStreaming) {
      e.preventDefault()
      handleSubmit(e as unknown as React.FormEvent)
    }
  }

  // 选择一个引用项（使用 hook 的 addMention 处理异步加载）
  const selectMention = async (item: MentionItem) => {
    // 移除输入框中的 @搜索词
    if (mentionAtIndex >= 0) {
      const before = value.substring(0, mentionAtIndex)
      setValue(before)
    }
    setMentionSearch("")
    setMentionAtIndex(-1)
    setMentionPopoverOpen(false)
    
    // hook 的 addMention 已包含异步加载逻辑
    await hookAddMention(item)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value
    setValue(newValue)
    
    // 如果弹窗打开，更新搜索词
    if (mentionPopoverOpen && mentionAtIndex >= 0) {
      // 获取 @ 后面的文本作为搜索词
      const searchText = newValue.substring(mentionAtIndex + 1)
      // 如果包含空格或换行，或者 @ 被删除，关闭弹窗
      if (searchText.includes(" ") || searchText.includes("\n") || mentionAtIndex >= newValue.length || newValue[mentionAtIndex] !== "@") {
        setMentionPopoverOpen(false)
        setMentionSearch("")
        setMentionAtIndex(-1)
      } else {
        setMentionSearch(searchText)
      }
      return
    }
    
    // 检测输入 @ 字符，自动打开引用选择
    if (newValue.endsWith("@") && textareaRef.current) {
      const textarea = textareaRef.current
      const atIndex = newValue.length - 1 // @ 的位置
      
      // 使用 canvas 精确测量文本宽度
      const canvas = document.createElement("canvas")
      const ctx = canvas.getContext("2d")
      const style = window.getComputedStyle(textarea)
      
      if (ctx) {
        ctx.font = `${style.fontSize} ${style.fontFamily}`
        
        // 获取当前行的文本（不包含最后的 @）
        const textBeforeAt = newValue.slice(0, -1)
        const lines = textBeforeAt.split("\n")
        const currentLineIndex = lines.length - 1
        const currentLineText = lines[currentLineIndex]
        
        // 测量当前行文本宽度
        const textWidth = ctx.measureText(currentLineText).width
        
        const lineHeight = parseInt(style.lineHeight) || 22
        const paddingTop = parseInt(style.paddingTop) || 12
        const paddingLeft = parseInt(style.paddingLeft) || 16
        
        // 位置：紧跟 @ 字符后面
        const top = paddingTop + (currentLineIndex * lineHeight) + lineHeight + 8
        const left = Math.min(paddingLeft + textWidth + 8, textarea.clientWidth - 288) // 288 = 弹窗宽度
        
        setMentionPosition({ top, left: Math.max(left, 12) })
        setMentionAtIndex(atIndex)
        setMentionSearch("")
        setMentionPopoverOpen(true)
      }
    }
  }

  const hasMentions = mentions.length > 0

  // 自动调整 textarea 高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px"
    }
  }, [value])

  // 点击外部关闭浮窗
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (mentionPopoverOpen && formRef.current && !formRef.current.contains(e.target as Node)) {
        setMentionPopoverOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [mentionPopoverOpen])

  return (
    <form ref={formRef} className={`${className} relative`} onSubmit={handleSubmit}>
      {/* 浮动的 @ 选择器 */}
      {mentionPopoverOpen && mentionPosition && (
        <div 
          className="absolute z-50 w-72 bg-white border border-neutral-200 rounded-xl shadow-lg overflow-hidden"
          style={{ top: mentionPosition.top, left: mentionPosition.left }}
        >
          {/* 搜索提示 */}
          {mentionSearch && (
            <div className="px-3 py-2 border-b border-neutral-100 text-xs text-neutral-500">
              搜索: <span className="text-neutral-900 font-medium">{mentionSearch}</span>
            </div>
          )}
          
          <div className="max-h-64 overflow-y-auto">
            {groupedMentions.video.length === 0 && groupedMentions.conversation.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm text-neutral-400">
                {mentionSearch ? "未找到匹配内容" : "暂无可引用的内容"}
              </div>
            ) : (
              <>
                {groupedMentions.video.length > 0 && (
                  <div>
                    <div className="px-3 py-1.5 text-xs text-neutral-400 font-medium">知识库视频</div>
                    {groupedMentions.video.slice(0, 8).map((item, index) => (
                      <div
                        key={`video-${item.id}`}
                        onClick={() => selectMention(item)}
                        className={`flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-neutral-50 transition-colors ${
                          index === 0 && groupedMentions.conversation.length === 0 ? "bg-neutral-50" : ""
                        }`}
                      >
                        <IconVideo className="size-4 text-neutral-400 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="truncate text-sm">{item.title}</div>
                          {item.subtitle && (
                            <div className="truncate text-xs text-neutral-400">{item.subtitle}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {groupedMentions.conversation.length > 0 && (
                  <div>
                    <div className="px-3 py-1.5 text-xs text-neutral-400 font-medium">历史对话</div>
                    {groupedMentions.conversation.slice(0, 5).map((item, index) => (
                      <div
                        key={`conv-${item.id}`}
                        onClick={() => selectMention(item)}
                        className={`flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-neutral-50 transition-colors ${
                          index === 0 && groupedMentions.video.length === 0 ? "bg-neutral-50" : ""
                        }`}
                      >
                        <IconMessage className="size-4 text-neutral-400 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="truncate text-sm">{item.title}</div>
                          {item.subtitle && (
                            <div className="truncate text-xs text-neutral-400">{item.subtitle}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {/* 提示 */}
                <div className="px-3 py-2 border-t border-neutral-100 text-xs text-neutral-400">
                  继续输入过滤 / Enter 选择 / Esc 取消
                </div>
              </>
            )}
          </div>
        </div>
      )}

      <div className="bg-white/80 backdrop-blur-sm border border-neutral-200/60 rounded-2xl shadow-sm hover:border-neutral-300 hover:shadow-md transition-all duration-200">
        {/* 顶部：提及区域 */}
        {hasMentions && (
          <div className="flex flex-wrap gap-1.5 px-3 pt-2 pb-1 border-b border-neutral-100">
            {mentions.map((mention) => (
              <Tooltip key={`${mention.type}-${mention.id}`}>
                <TooltipTrigger asChild>
                  <Badge
                    variant="secondary"
                    className={`h-6 gap-1 rounded-full cursor-pointer transition-colors ${
                      mention.loading 
                        ? "bg-amber-50 text-amber-700" 
                        : mention.content 
                          ? "bg-green-50 text-green-700 hover:bg-green-100" 
                          : "bg-neutral-100 hover:bg-neutral-200"
                    }`}
                    onClick={() => removeMention(mention)}
                  >
                    {mention.loading ? (
                      <span className="size-3 border-2 border-amber-300 border-t-amber-600 rounded-full animate-spin" />
                    ) : mention.type === "video" ? (
                      <IconVideo className="size-3" />
                    ) : (
                      <IconMessage className="size-3" />
                    )}
                    <span className="max-w-[120px] truncate text-xs">{mention.title}</span>
                    <IconX className="size-3 opacity-50" />
                  </Badge>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  {mention.loading 
                    ? "正在加载内容..." 
                    : mention.content 
                      ? `已加载 ${mention.content.length} 字符` 
                      : "点击移除"}
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
        )}

        {/* 中间：输入区域 */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="w-full px-4 py-3 bg-transparent resize-none outline-none text-neutral-900 placeholder:text-neutral-400 text-sm min-h-[44px] max-h-[200px] disabled:opacity-50"
          style={{ 
            height: "auto",
            overflow: value.split("\n").length > 5 ? "auto" : "hidden"
          }}
        />

        {/* 底部：工具栏 */}
        <div className="flex items-center justify-between gap-2 px-3 pb-2 pt-1">
          <div className="flex items-center gap-1">
            {/* @ 提及按钮 */}
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={() => {
                    // 在输入框底部显示
                    const textarea = textareaRef.current
                    if (textarea) {
                      const style = window.getComputedStyle(textarea)
                      const paddingTop = parseInt(style.paddingTop) || 12
                      const lineHeight = parseInt(style.lineHeight) || 22
                      const lines = value.split("\n")
                      const top = paddingTop + (lines.length * lineHeight) + 8
                      setMentionPosition({ top, left: 12 })
                    } else {
                      setMentionPosition({ top: 60, left: 12 })
                    }
                    setMentionPopoverOpen(true)
                  }}
                  className="h-7 px-2 flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100 rounded-full transition-colors"
                >
                  <IconAt className="size-4" />
                  {!hasMentions && <span>引用</span>}
                </button>
              </TooltipTrigger>
              <TooltipContent>引用视频或对话 (输入@触发)</TooltipContent>
            </Tooltip>

            {/* 附件按钮 - 暂未实现 */}
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={() => alert("附件功能开发中")}
                  className="size-7 flex items-center justify-center text-neutral-300 hover:text-neutral-400 rounded-full transition-colors cursor-not-allowed"
                >
                  <IconPaperclip className="size-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent>附件功能开发中</TooltipContent>
            </Tooltip>
          </div>

          <div className="flex items-center gap-1.5">
            {/* 模型选择 - 始终显示 */}
            <DropdownMenu open={modelMenuOpen} onOpenChange={setModelMenuOpen}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      className="h-7 px-2.5 flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100 rounded-full transition-colors"
                    >
                      <span className="max-w-[100px] truncate">{selectedModelDisplay}</span>
                      <IconChevronDown className="size-3" />
                    </button>
                  </DropdownMenuTrigger>
                </TooltipTrigger>
                <TooltipContent>选择模型</TooltipContent>
              </Tooltip>
              <DropdownMenuContent side="top" align="end" className="w-64">
                <DropdownMenuGroup>
                  <DropdownMenuLabel className="text-xs text-neutral-400">
                    选择对话模型
                  </DropdownMenuLabel>
                  {availableModels.length > 0 ? (
                    availableModels.map((m) => (
                      <DropdownMenuCheckboxItem
                        key={`${m.endpointId}-${m.model}`}
                        checked={selectedModel?.endpointId === m.endpointId && selectedModel?.model === m.model}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedModel({ endpointId: m.endpointId, model: m.model })
                          }
                        }}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="truncate text-sm">{m.model.split("/").pop() || m.model}</div>
                          <div className="truncate text-xs text-neutral-400">{m.endpointName}</div>
                        </div>
                      </DropdownMenuCheckboxItem>
                    ))
                  ) : (
                    <div className="px-2 py-3 text-xs text-neutral-400 text-center">
                      请在设置中配置 AI 端点
                    </div>
                  )}
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* 发送/停止按钮 */}
            {isStreaming ? (
              <button
                type="button"
                onClick={onCancel}
                className="size-8 flex items-center justify-center bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
                title="停止生成"
              >
                <IconPlayerStop className="size-4" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={disabled || !value.trim()}
                className="size-8 flex items-center justify-center bg-neutral-900 text-white rounded-full hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <IconArrowUp className="size-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </form>
  )
}
