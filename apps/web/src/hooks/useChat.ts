"use client"

import { useState, useCallback, useRef } from "react"
import { useRouter, usePathname } from "next/navigation"
import { conversationsApi, Conversation, ConversationDetail, Message } from "@/lib/api"

/**
 * 流式消息状态
 */
export interface StreamingState {
  isStreaming: boolean
  content: string
  reasoning: string
  chatId: number | null
}

/**
 * useChat Hook 返回类型
 */
export interface UseChatReturn {
  conversations: Conversation[]
  currentChatId: number | null
  currentChat: ConversationDetail | null
  isLoading: boolean
  streaming: StreamingState
  createNewChat: () => Promise<void>
  selectChat: (id: number | null) => Promise<void>
  deleteChat: (id: number) => Promise<void>
  sendMessageStream: (content: string, forceNewChat?: boolean) => Promise<void>
  cancelStream: () => void
  refreshConversations: () => Promise<void>
}

/**
 * 聊天逻辑 Hook
 * 
 * 管理对话列表、当前对话、流式消息等状态
 */
export function useChat(): UseChatReturn {
  const router = useRouter()
  const pathname = usePathname()
  
  // 对话状态
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentChatId, setCurrentChatId] = useState<number | null>(null)
  const [currentChat, setCurrentChat] = useState<ConversationDetail | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  
  // 流式状态
  const [streaming, setStreaming] = useState<StreamingState>({
    isStreaming: false,
    content: "",
    reasoning: "",
    chatId: null,
  })
  
  // 取消控制器
  const abortControllerRef = useRef<AbortController | null>(null)
  // 当前活跃的 chatId（避免闭包问题）
  const activeChatIdRef = useRef<number | null>(null)

  // 加载对话列表
  const refreshConversations = useCallback(async () => {
    try {
      const res = await conversationsApi.list()
      if (res.data) {
        setConversations(res.data)
      }
    } catch {
      // ignore
    }
  }, [])

  // 创建新对话
  const createNewChat = useCallback(async () => {
    // 取消正在进行的流式请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setStreaming({ isStreaming: false, content: "", reasoning: "", chatId: null })
    activeChatIdRef.current = null
    
    setCurrentChatId(null)
    setCurrentChat(null)
    if (pathname !== "/home") {
      router.push("/home")
    }
  }, [pathname, router])

  // 选择对话
  const selectChat = useCallback(async (id: number | null) => {
    // 取消正在进行的流式请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setStreaming({ isStreaming: false, content: "", reasoning: "", chatId: null })
    
    if (id === null) {
      setCurrentChatId(null)
      setCurrentChat(null)
      return
    }
    
    setIsLoading(true)
    try {
      const res = await conversationsApi.get(id)
      if (res.data) {
        setCurrentChatId(id)
        setCurrentChat(res.data)
        activeChatIdRef.current = id
        if (pathname !== "/home") {
          router.push("/home")
        }
      }
    } catch {
      // ignore
    } finally {
      setIsLoading(false)
    }
  }, [pathname, router])

  // 删除对话
  const deleteChat = useCallback(async (id: number) => {
    // 如果删除的是当前正在流式的对话，取消流式
    if (streaming.chatId === id && abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
      setStreaming({ isStreaming: false, content: "", reasoning: "", chatId: null })
    }
    
    try {
      await conversationsApi.delete(id)
      setConversations(prev => prev.filter(c => c.id !== id))
      if (currentChatId === id) {
        setCurrentChatId(null)
        setCurrentChat(null)
        activeChatIdRef.current = null
      }
    } catch {
      // ignore
    }
  }, [currentChatId, streaming.chatId])

  // 取消流式
  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setStreaming({ isStreaming: false, content: "", reasoning: "", chatId: null })
  }, [])

  // 流式发送消息
  const sendMessageStream = useCallback(async (content: string, forceNewChat: boolean = false): Promise<void> => {
    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()
    
    // 如果强制新对话或没有当前对话，创建一个
    let chatId = forceNewChat ? null : currentChatId
    if (!chatId) {
      try {
        const res = await conversationsApi.create()
        if (res.data) {
          chatId = res.data.id
          setCurrentChatId(chatId)
          setCurrentChat(null)
          refreshConversations()
        }
      } catch {
        return
      }
    }
    
    if (!chatId) return
    
    // 记录当前活跃的 chatId
    activeChatIdRef.current = chatId
    
    // 添加用户消息
    const tempUserMsg: Message = {
      id: -Date.now(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
      sources: null,
    }
    
    // 更新对话
    setCurrentChat(prev => {
      if (prev && prev.id === chatId) {
        return {
          ...prev,
          messages: [...prev.messages, tempUserMsg],
        }
      }
      return {
        id: chatId!,
        title: content.slice(0, 30) + (content.length > 30 ? "..." : ""),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        messages: [tempUserMsg],
      }
    })
    
    // 开始流式
    setStreaming({ isStreaming: true, content: "", reasoning: "", chatId })
    
    const signal = abortControllerRef.current?.signal
    if (!signal) return
    
    try {
      let fullContent = ""
      let fullReasoning = ""
      
      for await (const event of conversationsApi.sendMessageStream(chatId, content, signal)) {
        // 检查是否仍然是活跃的对话
        if (activeChatIdRef.current !== chatId) {
          break
        }
        
        if (event.type === "thinking") {
          fullReasoning += event.content || ""
          setStreaming(prev => ({ ...prev, reasoning: fullReasoning }))
        } else if (event.type === "content") {
          fullContent += event.content || ""
          setStreaming(prev => ({ ...prev, content: fullContent }))
        } else if (event.type === "done") {
          if (activeChatIdRef.current !== chatId) {
            return
          }
          
          const aiMessage: Message = {
            id: event.message_id || Date.now(),
            role: "assistant",
            content: fullContent,
            sources: event.reasoning ? JSON.stringify({ reasoning: event.reasoning }) : null,
            created_at: new Date().toISOString(),
          }
          
          setCurrentChat(prev => {
            if (!prev || prev.id !== chatId) return prev
            return {
              ...prev,
              messages: [...prev.messages, aiMessage],
            }
          })
          
          refreshConversations()
        } else if (event.type === "error") {
          console.error("Stream error:", event.error)
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") {
        // cancelled by user
      } else {
        console.error("Stream failed:", e)
      }
    } finally {
      abortControllerRef.current = null
      setStreaming({ isStreaming: false, content: "", reasoning: "", chatId: null })
    }
  }, [currentChatId, refreshConversations])

  return {
    conversations,
    currentChatId,
    currentChat,
    isLoading,
    streaming,
    createNewChat,
    selectChat,
    deleteChat,
    sendMessageStream,
    cancelStream,
    refreshConversations,
  }
}
