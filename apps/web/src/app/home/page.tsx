"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AliceInput } from "@/components/core/AliceInput";
import { VideoCard } from "@/components/core/VideoCard";
import { ChatView } from "@/components/features/ChatView";
import { useChatContext } from "./layout";
import { videosApi, importApi, authApi, suggestionsApi, Suggestion } from "@/lib/api";
import type { Video, InputIntent } from "@/types/home";

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "早上好";
  if (hour < 18) return "下午好";
  return "晚上好";
}

export default function DashboardPage() {
  const router = useRouter();
  const { currentChat, sendMessageStream, streaming, cancelStream } = useChatContext();
  const [recentVideos, setRecentVideos] = useState<Video[]>([]);
  const [videoCount, setVideoCount] = useState(0);
  const [username, setUsername] = useState<string>("");
  const [topTags, setTopTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [suggestionsContext, setSuggestionsContext] = useState<string>("");

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [videosRes, userRes, tagsRes, suggestionsRes] = await Promise.all([
        videosApi.list({ page: 1, page_size: 4 }),
        authApi.me(),
        videosApi.topTags(5),
        suggestionsApi.get(),
      ]);
      if (videosRes.data) {
        setRecentVideos(videosRes.data.items as Video[]);
        setVideoCount(videosRes.data.total);
      }
      if (userRes.data) {
        setUsername(userRes.data.username);
      }
      if (tagsRes.data?.tags) {
        setTopTags(tagsRes.data.tags.map(t => t.name));
      }
      if (suggestionsRes.data) {
        setSuggestions(suggestionsRes.data.suggestions);
        setSuggestionsContext(suggestionsRes.data.context || "");
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
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

  async function handleCommit(value: string, intent: InputIntent, context?: MentionContext) {
    if (intent === "import") {
      try {
        // 导入并立即触发处理
        const result = await importApi.singleAndProcess(value);
        loadData();
        // 跳转到视频详情页，可以看到处理进度
        router.push(`/home/video/${result.id}`);
      } catch (err) {
        console.error("Import failed:", err);
      }
    } else if (intent === "ask") {
      // 构建带上下文的消息
      let messageWithContext = value;
      
      // 如果有引用内容，添加到消息前面作为上下文
      if (context?.mentions && context.mentions.length > 0) {
        const contextParts = context.mentions
          .filter(m => m.content)
          .map(m => `[引用 ${m.type === "video" ? "视频" : "对话"}: ${m.title}]\n${m.content}`)
        
        if (contextParts.length > 0) {
          messageWithContext = `以下是引用的上下文内容:\n\n${contextParts.join("\n\n---\n\n")}\n\n---\n\n用户问题: ${value}`;
        }
      }
      
      // 首页的SmartInput总是开始新对话
      setIsSending(true);
      try {
        await sendMessageStream(messageWithContext, true); // forceNewChat=true
      } finally {
        setIsSending(false);
      }
    } else if (intent === "search") {
      // 去掉 /search 或 搜索 前缀
      const query = value.replace(/^(\/search\s+|搜索\s+)/i, "").trim();
      router.push(`/home/library?search=${encodeURIComponent(query)}`);
    }
  }

  // Chat 内发送消息（带上下文）
  async function handleSendInChatWithContext(value: string, context?: MentionContext) {
    if (!value.trim() || isSending || streaming.isStreaming) return;
    
    // 检测B站链接，自动转为导入
    const isBilibiliLink = value.includes("bilibili.com") || 
                           value.includes("b23.tv") || 
                           /\bBV[a-zA-Z0-9]+\b/.test(value);
    
    if (isBilibiliLink) {
      try {
        const result = await importApi.singleAndProcess(value);
        router.push(`/home/video/${result.id}`);
      } catch (err) {
        console.error("Import failed:", err);
      }
      return;
    }
    
    // 构建带上下文的消息
    let messageWithContext = value;
    if (context?.mentions && context.mentions.length > 0) {
      const contextParts = context.mentions
        .filter(m => m.content)
        .map(m => `[引用 ${m.type === "video" ? "视频" : "对话"}: ${m.title}]\n${m.content}`)
      
      if (contextParts.length > 0) {
        messageWithContext = `以下是引用的上下文内容:\n\n${contextParts.join("\n\n---\n\n")}\n\n---\n\n用户问题: ${value}`;
      }
    }
    
    setIsSending(true);
    try {
      await sendMessageStream(messageWithContext);
    } finally {
      setIsSending(false);
    }
  }

  // 有对话时显示对话界面
  if (currentChat) {
    return (
      <ChatView
        chat={currentChat}
        streaming={streaming}
        onSendMessage={handleSendInChatWithContext}
        onCancelStream={cancelStream}
        isSending={isSending}
      />
    );
  }

  // 原始欢迎页面
  return (
    <div className="h-full flex flex-col items-center justify-center p-6 md:p-12 relative overflow-y-auto">
      <div className="w-full max-w-2xl flex flex-col gap-10 z-10">
        {/* Welcome Text */}
        <div className="space-y-4 text-center md:text-left">
          <h1 className="text-4xl md:text-5xl font-light tracking-tight text-neutral-900">
            {getGreeting()}，{username || ""}
            <br />
            <span className="text-neutral-400">准备好学习了吗?</span>
          </h1>
          <p className="text-neutral-500 font-light text-lg">
            {videoCount > 0 ? (
              <>
                你的知识库已有{" "}
                <span className="text-neutral-900 font-medium">
                  {videoCount} 个视频
                </span>
                {topTags.length > 0 ? (
                  <>
                    ，涵盖
                    <br className="hidden md:inline" />
                    {topTags.slice(0, 3).join(" / ")} 等领域。
                  </>
                ) : "。"}
              </>
            ) : (
              <>
                开始导入你的第一个视频，
                <br className="hidden md:inline" />
                构建你的知识库。
              </>
            )}
          </p>
        </div>

        {/* Core Interaction */}
        <div>
          <AliceInput 
            onSubmit={(value, context) => handleCommit(value, "ask", context)} 
            placeholder="输入问题，或粘贴视频链接..."
            className="w-full" 
          />
        </div>

        {/* Recent Activity */}
        {recentVideos.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold text-neutral-400 uppercase tracking-widest">
                最近学习
              </h2>
              <button
                onClick={() => router.push("/home/library")}
                className="text-xs text-neutral-500 hover:text-neutral-900 transition-colors"
              >
                查看全部
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {recentVideos.slice(0, 2).map((video) => (
                <VideoCard key={video.id} video={video} layout="compact" />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
