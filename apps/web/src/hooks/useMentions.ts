"use client"

import { useState, useMemo, useCallback } from "react"
import { videosApi, Video, Conversation } from "@/lib/api"

/**
 * 可引用项类型
 */
export interface MentionItem {
  type: "video" | "conversation"
  id: number
  title: string
  subtitle?: string
  content?: string
  loading?: boolean
}

/**
 * useMentions Hook 配置
 */
export interface UseMentionsOptions {
  videos?: Video[]
  conversations?: Conversation[]
}

/**
 * useMentions Hook 返回类型
 */
export interface UseMentionsReturn {
  mentions: MentionItem[]
  mentionableItems: MentionItem[]
  filteredItems: MentionItem[]
  searchText: string
  isPopoverOpen: boolean
  setSearchText: (text: string) => void
  setPopoverOpen: (open: boolean) => void
  addMention: (item: MentionItem) => Promise<void>
  removeMention: (item: MentionItem) => void
  clearMentions: () => void
  getFirstMatch: () => MentionItem | null
}

/**
 * 引用逻辑 Hook
 * 
 * 管理 @引用 的选择、加载内容、过滤等
 */
export function useMentions(options: UseMentionsOptions = {}): UseMentionsReturn {
  const { videos = [], conversations = [] } = options
  
  const [mentions, setMentions] = useState<MentionItem[]>([])
  const [searchText, setSearchText] = useState("")
  const [isPopoverOpen, setPopoverOpen] = useState(false)

  // 构建可引用列表
  const mentionableItems = useMemo(() => {
    const items: MentionItem[] = []
    
    // 添加视频
    videos.forEach((video) => {
      if (!mentions.find((m) => m.type === "video" && m.id === video.id)) {
        items.push({
          type: "video",
          id: video.id,
          title: video.title,
          subtitle: video.author || undefined,
        })
      }
    })
    
    // 添加对话
    conversations.forEach((conv) => {
      if (!mentions.find((m) => m.type === "conversation" && m.id === conv.id)) {
        items.push({
          type: "conversation",
          id: conv.id,
          title: conv.title || `Dialog ${conv.id}`,
          subtitle: conv.message_count ? `${conv.message_count} messages` : undefined,
        })
      }
    })
    
    return items
  }, [videos, conversations, mentions])

  // 按搜索文本过滤
  const filteredItems = useMemo(() => {
    if (!searchText.trim()) {
      return mentionableItems
    }
    
    const query = searchText.toLowerCase()
    return mentionableItems.filter(
      (item) =>
        item.title.toLowerCase().includes(query) ||
        item.subtitle?.toLowerCase().includes(query)
    )
  }, [mentionableItems, searchText])

  // 获取第一个匹配项
  const getFirstMatch = useCallback((): MentionItem | null => {
    return filteredItems.length > 0 ? filteredItems[0] : null
  }, [filteredItems])

  // 添加引用（异步加载内容）
  const addMention = useCallback(async (item: MentionItem) => {
    // 先添加为 loading 状态
    const loadingItem: MentionItem = {
      ...item,
      loading: true,
    }
    setMentions((prev) => [...prev, loadingItem])
    setPopoverOpen(false)
    setSearchText("")

    // 如果是视频，加载转写内容
    if (item.type === "video") {
      try {
        const res = await videosApi.getTranscript(item.id)
        if (res.data) {
          // 截取前2000字符作为上下文
          const content = typeof res.data === "string" 
            ? res.data.slice(0, 2000)
            : res.data.text?.slice(0, 2000) || ""
          
          setMentions((prev) =>
            prev.map((m) =>
              m.type === item.type && m.id === item.id
                ? { ...m, content, loading: false }
                : m
            )
          )
        }
      } catch (error) {
        console.error("Failed to load transcript:", error)
        // 标记加载失败
        setMentions((prev) =>
          prev.map((m) =>
            m.type === item.type && m.id === item.id
              ? { ...m, loading: false, content: "[Failed to load]" }
              : m
          )
        )
      }
    } else {
      // 对话类型暂不加载内容
      setMentions((prev) =>
        prev.map((m) =>
          m.type === item.type && m.id === item.id
            ? { ...m, loading: false }
            : m
        )
      )
    }
  }, [])

  // 移除引用
  const removeMention = useCallback((item: MentionItem) => {
    setMentions((prev) => 
      prev.filter((m) => !(m.type === item.type && m.id === item.id))
    )
  }, [])

  // 清空所有引用
  const clearMentions = useCallback(() => {
    setMentions([])
  }, [])

  return {
    mentions,
    mentionableItems,
    filteredItems,
    searchText,
    isPopoverOpen,
    setSearchText,
    setPopoverOpen,
    addMention,
    removeMention,
    clearMentions,
    getFirstMatch,
  }
}
