# AliceLM 前端架构文档

> 版本: 2.1 | 更新: 2025-12-09 | 说明：结构保持不变，Chat 入口已走 `/api/agent/chat`，但 Agent 回放/确认/任务中心 UI 尚未实现，部分旧路由为占位需清理。

---

## 1. 架构概览

### 1.1 设计原则

| 原则 | 说明 | 实践 |
|------|------|------|
| **组件分层** | 原子 → 模式 → 功能 → 页面 | ui/ → patterns/ → features/ → pages/ |
| **关注点分离** | UI / 逻辑 / 数据分离 | components + hooks + api |
| **Design Token** | 统一设计语言 | 遵循 DESIGN_SYSTEM.md |
| **可复用性** | 组件通用化 | Props 驱动，无硬编码 |

### 1.2 目录结构

```
apps/web/src/
├── app/                      # Next.js App Router
│   ├── login/                # 登录页
│   ├── register/             # 注册页
│   ├── home/                 # 主应用 (需登录)
│   │   ├── page.tsx          # 首页/对话
│   │   ├── library/          # 知识库
│   │   ├── video/[id]/       # 视频详情
│   │   ├── settings/         # 设置
│   │   └── layout.tsx        # 带 Sidebar 布局
│   ├── layout.tsx            # 根布局
│   └── providers.tsx         # Context Providers
│
├── components/
│   ├── ui/                   # 原子组件 (shadcn, 26个)
│   │   ├── button.tsx
│   │   ├── badge.tsx
│   │   ├── input.tsx
│   │   └── ...
│   │
│   ├── patterns/             # 模式组件 (设计系统)
│   │   ├── ChatMessage.tsx   # 消息气泡
│   │   ├── ThinkingBlock.tsx # 思维链
│   │   └── index.ts
│   │
│   ├── core/                 # 核心组件
│   │   ├── AliceInput.tsx    # 智能输入框
│   │   ├── Sidebar.tsx       # 侧边栏
│   │   ├── VideoCard.tsx     # 视频卡片
│   │   └── theme-header.tsx  # 主题头部
│   │
│   ├── features/             # 功能组件
│   │   ├── ChatView/         # 对话视图
│   │   └── auth/             # 认证组件
│   │       ├── login-form.tsx
│   │       └── register-form.tsx
│   │
│   ├── video/                # 视频相关组件
│   │   ├── CommentsTab.tsx
│   │   ├── SummaryTab.tsx
│   │   ├── TranscriptTab.tsx
│   │   └── TabButton.tsx
│   │
│   ├── library/              # 知识库组件
│   ├── settings/             # 设置组件
│   └── landing/              # 落地页组件
│
├── hooks/                    # 自定义 Hooks
│   ├── useChat.ts            # 对话逻辑
│   ├── useMentions.ts        # @引用逻辑
│   └── index.ts
│
├── lib/
│   ├── api/                  # API 层 (按领域拆分, 10个模块)
│   │   ├── index.ts          # 导出
│   │   ├── client.ts         # Axios 实例
│   │   ├── videos.ts
│   │   ├── conversations.ts
│   │   ├── config.ts
│   │   └── auth.ts
│   └── utils/                # 工具函数
│
├── stores/                   # 状态管理 (可选 Zustand)
│   └── chat.ts
│
└── types/                    # TypeScript 类型
    ├── api.ts
    └── components.ts
```

---

## 2. 组件规范

### 2.1 组件分层

```
┌─────────────────────────────────────────────────────────────┐
│                        Pages (页面)                          │
│  app/dashboard/page.tsx                                     │
├─────────────────────────────────────────────────────────────┤
│                     Features (功能组件)                       │
│  AliceInput, ChatView, Sidebar, VideoPlayer                 │
├─────────────────────────────────────────────────────────────┤
│                     Patterns (模式组件)                       │
│  ChatMessage, ThinkingBlock, VideoCard, SourceRef           │
├─────────────────────────────────────────────────────────────┤
│                        UI (原子组件)                          │
│  Button, Badge, Input, Tooltip, Dialog, Dropdown            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 命名规范

| 类型 | 命名 | 示例 |
|------|------|------|
| 组件文件 | PascalCase | `ChatMessage.tsx` |
| Hook 文件 | camelCase + use | `useChat.ts` |
| API 文件 | camelCase | `conversations.ts` |
| 类型文件 | camelCase | `api.ts` |

### 2.3 组件模板

```tsx
// components/patterns/ChatMessage.tsx
"use client"

import { cn } from "@/lib/utils"
import { Avatar } from "@/components/ui/avatar"

interface ChatMessageProps {
  role: "user" | "assistant"
  content: string
  reasoning?: string
  sources?: string[]
  className?: string
}

export function ChatMessage({
  role,
  content,
  reasoning,
  sources,
  className,
}: ChatMessageProps) {
  return (
    <div className={cn(
      "flex gap-3",
      role === "user" ? "justify-end" : "justify-start",
      className
    )}>
      {/* ... */}
    </div>
  )
}
```

---

## 3. Hooks 规范

### 3.1 Hook 职责

| Hook | 职责 | 依赖 |
|------|------|------|
| `useChat` | 对话消息、流式输出、发送 | conversationsApi |
| `useVideos` | 视频列表、搜索、导入 | videosApi |
| `useConfig` | 配置读取、模型列表 | configApi |
| `useMentions` | @引用、内容加载 | videosApi |

### 3.2 Hook 模板

```tsx
// hooks/useChat.ts
import { useState, useCallback } from "react"
import { conversationsApi } from "@/lib/api"

interface UseChatOptions {
  onError?: (error: Error) => void
}

export function useChat(options?: UseChatOptions) {
  const [messages, setMessages] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)

  const sendMessage = useCallback(async (content: string) => {
    // ...
  }, [])

  const cancelStream = useCallback(() => {
    // ...
  }, [])

  return {
    messages,
    isStreaming,
    sendMessage,
    cancelStream,
  }
}
```

---

## 4. API 层规范

### 4.1 文件拆分

```
lib/api/
├── index.ts          # 统一导出
├── client.ts         # Axios 实例 + 拦截器
├── videos.ts         # 视频相关
├── conversations.ts  # 对话相关
├── config.ts         # 配置相关
├── auth.ts           # 认证相关
└── types.ts          # API 类型定义
```

### 4.2 API 模板

```tsx
// lib/api/videos.ts
import { client } from "./client"
import type { Video, PaginatedResponse } from "./types"

export const videosApi = {
  list: (params?: { page?: number; search?: string }) =>
    client.get<PaginatedResponse<Video>>("/videos", { params }),
  
  get: (id: number) =>
    client.get<Video>(`/videos/${id}`),
  
  getTranscript: (id: number) =>
    client.get(`/videos/${id}/transcript`),
}
```

---

## 5. 迁移计划

### Phase 1: 组件抽取 (本次)

- [ ] 创建 `patterns/ChatMessage.tsx`
- [ ] 创建 `patterns/ThinkingBlock.tsx`
- [ ] 创建 `features/ChatView/index.tsx`
- [ ] 重构 `dashboard/page.tsx`
- [ ] 删除废弃组件

### Phase 2: Hooks 抽取

- [ ] 创建 `hooks/useChat.ts`
- [ ] 创建 `hooks/useMentions.ts`
- [ ] 从 layout.tsx 迁移 ChatContext

### Phase 3: API 层重构

- [ ] 拆分 `lib/api.ts` 为多文件
- [ ] 创建 `lib/api/client.ts`

### Phase 4: 清理

- [ ] 删除 `*-demo.tsx` 文件
- [ ] 删除 `notion-prompt-form.tsx`
- [ ] 删除未使用组件

---

## 6. Design System 集成

所有组件必须遵循 `DESIGN_SYSTEM.md`:

| Token | 用途 | 值 |
|-------|------|-----|
| `bg-neutral-900` | 用户消息背景 | #171717 |
| `bg-white border-neutral-200` | AI消息背景 | - |
| `rounded-2xl` | 消息圆角 | 16px |
| `text-sm` | 消息文字 | 14px |
| `bg-amber-50` | 思维链背景 | - |
| `duration-300` | 动画时长 | 300ms |
