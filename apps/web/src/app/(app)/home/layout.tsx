"use client";

import { useState, useEffect, createContext, useContext } from "react";
import { useRouter } from "next/navigation";
import { Menu } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { Sidebar } from "@/components/core/Sidebar";
import { useChat, UseChatReturn } from "@/hooks";
import { videosApi, authApi } from "@/lib/api";

// 对话上下文 - 使用 useChat hook 的返回类型
const ChatContext = createContext<UseChatReturn | null>(null);

export function useChatContext() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChatContext must be used within DashboardLayout");
  }
  return context;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [videoCount, setVideoCount] = useState(0);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  // 使用 useChat hook 管理所有对话逻辑
  const chat = useChat();

  useEffect(() => {
    // 检查登录状态
    const token = localStorage.getItem("token");
    if (!token) {
      router.replace("/login");
      return;
    }

    // 验证 token 有效性
    authApi.me().then(() => {
      setIsAuthenticated(true);
      // 获取视频数量
      videosApi.list({ page: 1, page_size: 1 }).then((res) => {
        if (res.data?.total) {
          setVideoCount(res.data.total);
        }
      }).catch(() => {});
      // 加载对话列表
      chat.refreshConversations();
    }).catch(() => {
      localStorage.removeItem("token");
      router.replace("/login");
    });
  }, [router]);

  // 加载中状态
  if (isAuthenticated === null) {
    return (
      <div className="h-screen flex items-center justify-center bg-neutral-50">
        <Spinner className="w-8 h-8 text-neutral-400" />
      </div>
    );
  }

  return (
    <ChatContext.Provider value={chat}>
      <div className="flex h-screen bg-neutral-50 text-neutral-900 font-sans overflow-hidden">
        <Sidebar
          conversations={chat.conversations}
          videoCount={videoCount}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
          onNewChat={chat.createNewChat}
          onSelectChat={chat.selectChat}
          onDeleteChat={chat.deleteChat}
          currentChatId={chat.currentChatId}
        />

        <main className="flex-1 flex flex-col min-w-0 relative bg-neutral-50/50">
          {/* Mobile Header */}
          <div className="md:hidden absolute top-4 left-4 z-50">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 bg-white rounded-lg shadow-sm border border-neutral-200 text-neutral-600"
            >
              <Menu size={20} />
            </button>
          </div>

          {/* Backdrop for Mobile */}
          {sidebarOpen && (
            <div
              className="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 md:hidden"
              onClick={() => setSidebarOpen(false)}
            />
          )}

          <div className="flex-1 overflow-hidden relative">{children}</div>
        </main>
      </div>
    </ChatContext.Provider>
  );
}
