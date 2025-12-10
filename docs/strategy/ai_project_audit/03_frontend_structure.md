# 前端结构与页面流程

**项目名称**: AliceLM Web
**文档生成时间**: 2025-12-09
**数据来源**: 代码仓库静态分析 (apps/web/src/)

---

## 技术栈概览

### 框架与运行时
| 类别 | 技术选型 | 版本 | 说明 |
|------|----------|------|------|
| 前端框架 | Next.js (App Router) | 15.1.0 | `app/` 目录结构，支持 SSR/ISR，Turbopack dev (`apps/web/package.json`) |
| 视图库 | React | 19.0.0 | 函数组件、`use client` 指令用于客户端页面 |
| 语言 | TypeScript | 5.x | 全量 TS，组件/Hook 有类型注解 |
| 网络库 | Axios | 1.7.0 | 统一实例 `lib/api/client.ts:1`，拦截器处理 Token/401 |
| 动画 | Framer Motion | 11.18.2 | 用于 Chat 消息/渐显 (`components/features/ChatView/index.tsx:71`) |
| 状态工具 | @tanstack/react-query | 5.x | Provider 挂载于 `app/providers.tsx:6-21`，页面暂未使用查询 Hook |
| 样式 | Tailwind CSS | 4.x | 原子类写法贯穿组件，未使用全局 Design Tokens |
| 图标 | lucide-react / @tabler/icons-react | 0.460.0 / 3.35.0 | 页面和输入控件大量使用 |
| 字体 | GeistSans | 1.5.1 | 全局字体加载 `app/layout.tsx:2-23` |

### 状态管理
- 本地状态+自定义 Hook：核心聊天状态由 `useChat` 管理（`hooks/useChat.ts:39-282`），@引用状态由 `useMentions` 管理（`hooks/useMentions.ts:48-181`）。
- React Query 仅提供 Provider（`app/providers.tsx:6-21`），当前页面数据获取均用 `useEffect` + axios 直调，无缓存/失效策略。
- 认证状态通过 `localStorage.token` 判断，`(app)/home/layout.tsx:35-57` 在首屏校验并根据结果重定向。

### UI 组件库
- Radix UI 原子组件封装：按钮、输入、弹窗等通过 `components/ui/*.tsx` 自建封装。
- Lucide/Tabler 图标：交互按钮、状态提示使用 `lucide-react`（如 `ArrowLeft`、`Loader2`）与 `@tabler/icons-react`（如输入栏的 Icon）。
- 动画与文本：`components/ui/animated-text.tsx`、Framer Motion（Chat 视图过渡）。
- 其他：`qrcode.react` 用于设置页扫码（`app/(app)/home/settings/page.tsx:4-21` 中引入）。

---

## 目录结构

> 完整列出 `apps/web/src/` 目录及用途。

```
apps/web/src/
├─ app/
│  ├─ layout.tsx                # 根布局，加载 Geist 字体与 TooltipProvider
│  ├─ globals.css               # 全局样式
│  ├─ providers.tsx             # React Query Provider 包裹
│  ├─ page.tsx                  # 落地页，组合 landing 组件
│  ├─ login/page.tsx            # 登录页容器
│  ├─ register/page.tsx         # 注册页容器
│  ├─ (app)/                    # 业务分组（需登录的区域）
│  │  ├─ home/layout.tsx        # Dashboard 布局 + Chat 上下文 + Sidebar
│  │  ├─ home/page.tsx          # 首页/仪表盘 + SmartInput + ChatView
│  │  ├─ home/video/[id]/page.tsx   # 视频详情页
│  │  ├─ home/library/page.tsx      # 知识库 & B 站收藏夹
│  │  ├─ home/graph/page.tsx        # 知识图谱页面
│  │  ├─ home/settings/page.tsx     # 设置中心（多 Tab）
│  │  ├─ video/[id]/page.tsx        # 旧版视频详情占位（未挂载鉴权）
│  │  ├─ library/page.tsx           # 旧版知识库占位
│  │  ├─ graph/page.tsx             # 旧版图谱占位
│  │  ├─ tasks/page.tsx             # 占位
│  │  ├─ chat/page.tsx              # 占位
│  │  ├─ timeline/page.tsx          # 占位
│  │  ├─ console/page.tsx           # 占位
│  │  ├─ settings/page.tsx          # 占位
│  │  └─ video/[id]/                # 占位目录
├─ components/
│  ├─ core/                        # 核心复用组件（Sidebar、AliceInput、VideoCard 等）
│  ├─ ui/                          # 原子 UI 封装 (Button, Input, Tooltip...)
│  ├─ landing/                     # 落地页模块（Header/Hero/Featured/Promo/Footer）
│  ├─ patterns/                    # Chat 视觉模式 (ChatMessage/ThinkingBlock)
│  ├─ features/                    # 功能组件 (ChatView, auth forms)
│  ├─ library/                     # 知识库/B 站卡片组件
│  ├─ settings/                    # 设置页子组件（appearance 等）
│  └─ video/                       # 视频详情 Tab 组件
├─ hooks/
│  ├─ useChat.ts                   # 对话与流式状态管理
│  ├─ useMentions.ts               # @引用选择逻辑
│  └─ index.ts                     # Hook 聚合导出
├─ lib/
│  ├─ api/                         # 前端 API 客户端与各模块方法
│  │  ├─ client.ts                 # Axios 实例与拦截器
│  │  ├─ auth.ts                   # 认证模块
│  │  ├─ videos.ts                 # 视频/导入/队列
│  │  ├─ conversations.ts          # 对话与 SSE 流
│  │  ├─ config.ts                 # 配置/LLM/Prompt
│  │  ├─ bilibili.ts               # B 站绑定与收藏夹
│  │  ├─ folders.ts                # 收藏夹监控
│  │  ├─ knowledge.ts              # 知识图谱/学习统计
│  │  ├─ system.ts                 # 存储/QA/建议
│  │  ├─ types.ts                  # 所有 API 类型定义
│  │  └─ index.ts                  # API/类型统一导出
│  └─ utils.ts                     # 工具方法 (cn 等)
├─ types/
│  └─ home.ts                      # 前端 Domain 类型（Video/Transcript 等）
```

### 布局与运行机制
- 根布局 `app/layout.tsx:6-24`：设置 `<html lang="zh-CN">`，应用 GeistSans 字体并包裹 TooltipProvider，所有页面共享。
- 业务布局 `(app)/home/layout.tsx:22-107`：负责鉴权与注入 Sidebar/Chat Context；移动端提供菜单开关；加载视频计数与会话列表。
- Provider 装载 `app/providers.tsx:6-21`：为后续扩展 React Query 做好包裹，当前 children 仅传递 QueryClientProvider。
- 全局样式 `app/globals.css`：Tailwind 原子类基础，未启用 CSS Modules；需注意在全局引入顺序保持在布局顶层。

### 数据模型与类型
- `types/home.ts:3-22` 定义 Video/VideoDetail 以 `bvid` 作为主键，包含 `status/summary/cover_url` 等；`TranscriptSegment` 描述转写时间片。
- `lib/api/types.ts`（未全文列出）包含 Config/Conversation/Prompt/LLMEndpoint 等接口类型，供 API 方法泛型使用。
- 组件直接引用 `Video` 类型（`components/core/VideoCard.tsx:7-11`、`app/(app)/home/page.tsx:22`），Conversation 类型从 API 导出（`components/core/Sidebar.tsx:7-19`）。
- 建议将 `source_type/source_id` 补充到前端类型以符合架构规范，并在 API 适配层做映射。

---

## 路由与页面一览

### 路由概览
| 路由 | 组件文件 | 需登录 | 布局 | 说明 |
|------|----------|--------|------|------|
| `/` | `apps/web/src/app/page.tsx:1` | 否 | `app/layout.tsx:6-23` | 落地页，组合 landing 模块 |
| `/login` | `apps/web/src/app/login/page.tsx:1` | 否 | 根布局 | 登录表单容器 |
| `/register` | `apps/web/src/app/register/page.tsx:1` | 否 | 根布局 | 注册表单容器 |
| `/home` | `apps/web/src/app/(app)/home/page.tsx:1` | 是 | `(app)/home/layout.tsx:22-107` | 仪表盘 + SmartInput + ChatView |
| `/home/video/[id]` | `apps/web/src/app/(app)/home/video/[id]/page.tsx:1` | 是 | `(app)/home/layout.tsx` | 视频详情/摘要/转写/评论 |
| `/home/library` | `apps/web/src/app/(app)/home/library/page.tsx:1` | 是 | `(app)/home/layout.tsx` | 知识库与 B 站收藏夹管理 |
| `/home/graph` | `apps/web/src/app/(app)/home/graph/page.tsx:1` | 是 | `(app)/home/layout.tsx` | 知识图谱可视化 |
| `/home/settings` | `apps/web/src/app/(app)/home/settings/page.tsx:1` | 是 | `(app)/home/layout.tsx` | 设置中心 (LLM/队列/存储等) |

### 1. 落地页 `/`
- 文件: `apps/web/src/app/page.tsx:1`（引入 Header/Hero/Featured/Promo/Footer）。
- 功能: 静态展示宣传内容，未接入 API；主结构包含主视觉、特性区、推广、页脚。
- 组件: `Header`、`Hero`、`Featured`、`Promo`、`Footer`（均位于 `components/landing/`）。

### 2. 登录页 `/login`
- 文件: `apps/web/src/app/login/page.tsx:1-9`（容器）；核心表单 `components/features/auth/login-form.tsx:1-166`。
- 功能: 邮箱+密码登录，提交 `authApi.login`，成功后存储 token 并跳转 `/home`（`login-form.tsx:22-38`）。
- 组件: `Card`/`Input`/`Button`（UI 封装），`Loader2` 加载态，背景图 `Image`。

### 3. 注册页 `/register`
- 文件: `apps/web/src/app/register/page.tsx:1-10`；表单 `components/features/auth/register-form.tsx:1-128`。
- 功能: 填写用户名/邮箱/密码，调用 `authApi.register`，写入 token 后跳转 `/home`（`register-form.tsx:23-39`）。
- 组件: 与登录一致，复用 UI 原子件。

### 4. 主页 `/home`
- 文件: `apps/web/src/app/(app)/home/page.tsx:1-236`。
- 功能: 欢迎面板 + SmartInput；展示最近学习视频与标签；当有 `currentChat` 时切换到 ChatView。
- 主要逻辑: 
  - 初始数据加载 `loadData()` 通过 `useEffect` 触发（`home/page.tsx:31-62`）。
  - 输入提交 `handleCommit` 支持提问/导入/搜索分支（`home/page.tsx:75-113`）。
  - Chat 场景下 `handleSendInChatWithContext` 处理 @引用与 B 站链接导入（`home/page.tsx:115-152`）。
- 组件: `AliceInput`、`VideoCard`、`ChatView`、`Sidebar` (由布局提供)。

### 5. 视频详情 `/home/video/[id]`
- 文件: `apps/web/src/app/(app)/home/video/[id]/page.tsx:1-322`。
- 功能: 根据视频 id 拉取详情、转写、评论；轮询处理状态，三 Tab 切换摘要/转写/评论。
- 主要逻辑: `loadVideo` 请求 `videosApi.get` 并按状态启动轮询（`page.tsx:41-95`）；`loadComments` 分页获取评论（`page.tsx:107-125`）。
- 组件: `TabButton`、`SummaryTab`、`TranscriptTab`、`CommentsTab`（`components/video/`）。

### 6. 知识库 `/home/library`
- 文件: `apps/web/src/app/(app)/home/library/page.tsx:1-476`。
- 功能: 
  - “我的知识库”视图：筛选视频状态、搜索转写内容、网格展示 `VideoCard`（`page.tsx:191-278`）。
  - “B站收藏夹”视图：列出/添加/导入收藏夹，支持合辑/订阅分类（`page.tsx:324-416`）。
  - 收藏夹详情与单视频导入（`page.tsx:280-322`）。
- API: `videosApi.list`、`videosApi.topTags`、`bilibiliApi.getFolders/getFolderVideos`、`foldersApi.add`、`importApi.single`。

### 7. 知识图谱 `/home/graph`
- 文件: `apps/web/src/app/(app)/home/graph/page.tsx:1-303`。
- 功能: 调用 `knowledgeApi.getGraph` 构建概念/视频节点；点击概念加载相关视频与关联概念（`page.tsx:37-57`）。
- 交互: 内置缩放/重置（`page.tsx:114-135`），节点布局以简单圆形分布，最多渲染50条连线。

### 8. 设置页 `/home/settings`
- 文件: `apps/web/src/app/(app)/home/settings/page.tsx:1-1940`（多 Tab 组合）。
- 功能与分区：
  - 个人信息/B 站绑定/收藏夹管理（`page.tsx:23-208`）。
  - ASR 配置（`page.tsx:211-335`）、LLM 端点与模型选择（`page.tsx:337-511`）。
  - 模型任务、Prompt 编辑（`page.tsx:513-1518` 部分段落）。
  - 处理队列监控（`page.tsx:1529-1781`）、存储清理（`page.tsx:1784-1936`）。
  - API: `configApi.*`、`bilibiliApi.*`、`foldersApi.*`、`videosApi.*`、`systemApi.*`、`authApi.me`。

### 其他占位路由（需清理或重定向）
- `/video/[id]` (`apps/web/src/app/(app)/video/[id]/page.tsx`)：旧版视频详情骨架。
- `/library` (`apps/web/src/app/(app)/library/page.tsx`)：旧版知识库骨架。
- `/graph` (`apps/web/src/app/(app)/graph/page.tsx`)：旧版图谱骨架。
- `/tasks` (`apps/web/src/app/(app)/tasks/page.tsx`)：占位。
- `/chat` (`apps/web/src/app/(app)/chat/page.tsx`)：占位。
- `/timeline` (`apps/web/src/app/(app)/timeline/page.tsx`)：占位。
- `/console` (`apps/web/src/app/(app)/console/page.tsx`)：占位。
- `/settings` (`apps/web/src/app/(app)/settings/page.tsx`)：占位。
- 这些路由未包含鉴权与业务逻辑，建议统一跳转至 `/home/*` 对应页面或删除。

---

## 组件架构

### 目录结构
- `components/core/`：AliceInput、VideoCard、Sidebar、theme-header。
- `components/ui/`：Button/Input/Switch/Tooltip/Dialog/Select 等原子件。
- `components/features/`：ChatView、auth 登录/注册表单。
- `components/patterns/`：ChatMessage、ThinkingBlock（思维链）。
- `components/landing/`：落地页模块。
- `components/library/`：收藏夹与 B 站视频卡片。
- `components/video/`：详情页 Tab 组件。
- `components/settings/`：外观设置等（当前仅 `appearance-settings.tsx`）。

### 核心组件 (components/core/)
- `AliceInput` (`components/core/AliceInput.tsx:1-556`):
  - 功能: 智能输入框，支持 @引用视频/对话、模型选择、流式取消；加载配置与视频列表（`AliceInput.tsx:85-111`）。
  - Props: `onSubmit`、`onCancel`、`placeholder`、`disabled`、`isStreaming`、`className`、`conversations`（`AliceInput.tsx:33-48`）。
  - 引用逻辑: @ 触发弹窗、`useMentions` 分组视频/对话（`AliceInput.tsx:75-131`），选择后加载转写片段（依赖 `useMentions`）。
  - 模型选择: 从配置端点提取 chat 类型模型，Dropdown 列表（`AliceInput.tsx:134-175`、`487-531`）。
- `VideoCard` (`components/core/VideoCard.tsx:1-170`):
  - 功能: 视频封面卡片，支持 `grid` 与 `compact` 两种布局（`VideoCard.tsx:39-100`）。
  - Props: `video`、`layout`；展示处理状态、时长、创建时间（`VideoCard.tsx:40-167`）。
- `Sidebar` (`components/core/Sidebar.tsx:1-203`):
  - 功能: 左侧导航与对话列表，移动端支持收起；触发新建/选择/删除对话（`Sidebar.tsx:37-120`）。
  - 导航: 知识库/图谱/设置链接（`Sidebar.tsx:138-164`）。
- `theme-header.tsx` (`components/core/theme-header.tsx`): 顶部主题头部（未在主流程使用）。

### UI 基础组件 (components/ui/)
- 列表（均为 TSX 封装 Radix/自定义样式）：`button.tsx`、`card.tsx`、`input.tsx`、`textarea.tsx`、`select.tsx`、`slider.tsx`、`popover.tsx`、`dialog.tsx`、`tooltip.tsx`、`switch.tsx`、`radio-group.tsx`、`dropdown-menu.tsx`、`badge.tsx`、`separator.tsx`、`avatar.tsx`、`command.tsx`、`item.tsx`、`empty.tsx`、`animated-text.tsx`、`button-group.tsx`、`input-group.tsx`、`field.tsx`、`label.tsx`、`checkbox.tsx`、`kbd.tsx`、`spinner.tsx` 等。
- 用途示例: 登录表单使用 `Input`/`Button`/`Card`（`components/features/auth/login-form.tsx:43-165`）；Chat 流式消息用 `AnimatedTextWithCursor`（`components/features/ChatView/StreamingMessage.tsx:35-41`）。

### 功能组件 (components/features/)
- `ChatView` (`components/features/ChatView/index.tsx:38-116`): 显示聊天记录、流式消息、输入框；解析 AI reasoning（`index.tsx:58-68`）。
- `StreamingMessage` (`components/features/ChatView/StreamingMessage.tsx:12-56`): 流式回复气泡，展示思维链与逐词动画。
- `Auth` 表单: `login-form.tsx:22-93` 提交登录，`register-form.tsx:23-103` 提交注册。

### 页面组件
- 落地页模块: `components/landing/header.tsx`（导航与登录入口）、`hero.tsx`（主视觉 CTA）、`featured.tsx`（特性列表）、`promo.tsx`（推广段落）、`footer.tsx`（页脚链接）；组合于 `components/landing/index.tsx` 供 `app/page.tsx` 使用。
- 视频详情 Tab: `components/video/SummaryTab.tsx`（摘要/概念/标签展示）、`TranscriptTab.tsx`（逐字稿滚动）、`CommentsTab.tsx`（评论列表与加载更多）、`TabButton.tsx`（Tab 切换按钮）。
- 知识库: `components/library/FolderCard.tsx`（收藏夹卡片，含添加/打开操作）、`BilibiliVideoCard.tsx`（收藏夹视频条目与导入按钮）、`index.ts` 聚合导出。
- Pattern: `ChatMessage.tsx:18-101` (消息气泡，含思维链)、`ThinkingBlock.tsx:23-95` (思维链折叠/流式)，`patterns/index.ts` 提供统一出口。
- 设置: `components/settings/appearance-settings.tsx`（外观设置，占位），未来可扩展为更多设置子模块。

### 落地页与营销体验（补充）
- 结构: 主视觉 `Hero` 使用大号排版与 CTA（`components/landing/hero.tsx`），突出核心卖点“B站视频转化知识库”。
- 特性列表: `Featured` 列出三列特性卡片，强调“AI 摘要”“知识图谱”“转写搜索”（文件行号需进一步索引）。
- Promo 与 Footer: 提供转化按钮与社交链接，当前文案静态，未接入分析/埋点。

---

## 认证与访问控制
- Token 存储：登录/注册成功后写入 `localStorage.token`（`components/features/auth/login-form.tsx:29-31`），拦截器读取并附加到请求（`lib/api/client.ts:14-21`）。
- 初始校验：`(app)/home/layout.tsx:35-57` 在客户端读取 token，调用 `authApi.me` 验证；失败则移除 token 并 `router.replace("/login")`。
- 路由覆盖：`/home/*` 页面均通过 `(app)/home/layout` 包裹；其他旧路由未校验，需重定向或删除（见“其他占位路由”）。
- SSE 安全：`sendMessageStream` 直接带 Bearer 头访问流式端点（`lib/api/conversations.ts:31-42`），依赖本地存储的 token，有效性过期会在后续请求中抛出错误但未统一处理。
- 敏感日志：部分 `catch` 直接 `console.error` 输出（`home/page.tsx:83-85`、`home/video/[id]/page.tsx:210-216`），需避免暴露凭证信息。

## 数据获取与缓存策略
- axios 直调：页面采用 `useEffect` + axios，未使用 React Query 导致缓存失效、重复请求（如首页并行 `videosApi.list`/`authApi.me`/`videosApi.topTags`，`home/page.tsx:35-56`）。
- 轮询：视频状态轮询固定 3s （`home/video/[id]/page.tsx:75-95`），队列轮询 5s (`home/settings/page.tsx:1535-1540`)，需注意资源占用与暂停条件。
- 错误处理：多数 API `catch` 空处理，UI 反馈缺失，除少数 alert（`home/library/page.tsx:139-154`）和提示框外未统一封装。
- 模型/配置加载：`AliceInput` 在客户端单独请求配置和视频列表（`AliceInput.tsx:85-111`），与 Dashboard/Settings 逻辑重复，可引入全局缓存或 React Query 共享。

---

## Hooks 与状态管理

### useChat Hook
- 文件: `apps/web/src/hooks/useChat.ts:39-282`。
- 状态结构: `conversations`、`currentChatId`、`currentChat`、`isLoading`、`streaming` (包含 `content/reasoning/chatId/isStreaming`)；内部 `abortControllerRef` 与 `activeChatIdRef`。
- 方法:
  - `refreshConversations` 拉取列表 (`useChat.ts:62-72`)
  - `createNewChat` 重置状态并跳转 `/home` (`useChat.ts:75-89`)
  - `selectChat` 获取会话详情并更新当前会话 (`useChat.ts:92-122`)
  - `deleteChat` 删除并清理流式状态 (`useChat.ts:124-144`)
  - `sendMessageStream` 发送消息并消费 SSE，必要时创建新会话 (`useChat.ts:156-268`)
  - `cancelStream` 终止流式 (`useChat.ts:146-154`)
- 使用示例: `(app)/home/layout.tsx:32-54` 获取实例并通过 Context 提供；`(app)/home/page.tsx:21-22` 调用 `sendMessageStream`。

### useMentions Hook
- 文件: `apps/web/src/hooks/useMentions.ts:48-181`。
- 状态结构: `mentions`（已选项，含 `loading/content`）、`searchText`、`isPopoverOpen`。
- 方法: `addMention`（加载转写或标记失败，`useMentions.ts:105-155`）、`removeMention`、`clearMentions`、`getFirstMatch`。
- 数据来源: 传入视频/会话列表后构建 `mentionableItems`，按标题/副标题过滤（`useMentions.ts:55-99`）。
- 使用示例: `AliceInput` 在 @ 输入时调用 `addMention` 并展示 Badge（`components/core/AliceInput.tsx:247-376`）。

---

## API 客户端层

### 客户端配置
- 文件: `apps/web/src/lib/api/client.ts:1-39`。
- 基础 URL: `/api/v1`，超时 30s（`client.ts:8-11`）。
- 拦截器: 请求拦截附带 `Authorization: Bearer ${token}` 从 `localStorage` 读取（`client.ts:14-21`）；响应拦截 401 时清理 token 并跳转 `/login`（`client.ts:25-38`）。

### API 模块
| 模块 | 文件 | 方法 | 对应后端端点 |
|------|------|------|-------------|
| 认证 | `lib/api/auth.ts:8-27` | `login`/`register`/`me`/`logout`/`updateProfile`/`changePassword` | `/auth/*` |
| 视频 | `lib/api/videos.ts:19-48` | `list`/`get`/`getTranscript`/`delete`/`reprocess`/`stats`/`topTags`/`processNow`/`getStatus`/`getComments`/`getQueue`/`cancelProcess`/`removeFromQueue` | `/videos/*` |
| 导入 | `lib/api/videos.ts:50-68` | `single`/`batch`/`singleAndProcess` | `/videos`、`/videos/batch`、`/videos/{id}/process` |
| 对话 | `lib/api/conversations.ts:8-77` | `list`/`create`/`get`/`delete`/`sendMessageStream` | `/conversations/*` 及 `/conversations/{id}/messages/stream` (SSE) |
| 配置 | `lib/api/config.ts:19-74` | `get`/`updateASR`/`updateLLM`/`updateNotify`/`getASRProviders`/`getLLMProviders`/`fetchLLMModels`/`createLLMEndpoint`/`deleteLLMEndpoint`/`refreshEndpointModels`/`updateModelTasks`/`updateSingleModelTask`/`getPrompts`/`updatePrompt`/`resetPrompt` | `/config/*` |
| B站 | `lib/api/bilibili.ts:14-31` | `getQRCode`/`pollQRCode`/`getStatus`/`unbind`/`getFolders`/`getFolderVideos` | `/bilibili/*` |
| 收藏夹 | `lib/api/folders.ts:8-18` | `list`/`add`/`delete`/`scan`/`toggle` | `/folders/*` |
| 知识图谱 | `lib/api/knowledge.ts:75-120` | `getGraph`/`getConceptVideos`/`getRelatedConcepts`/`getLearningStats`/`getWeeklyReport`/`getReviewSuggestions` | `/knowledge/*` |
| 系统/QA/建议 | `lib/api/system.ts:8-27` | `getStorage`/`cleanup`/`qaApi.ask/search/summarize`/`suggestionsApi.get` | `/system/*` `/qa/*` `/suggestions` |

---

## 典型用户流程

### 流程1: 用户注册/登录
1. 访问 `/login` 或 `/register`（页面容器 `app/login/page.tsx:3-9`）。
2. 填写表单并提交，调用 `authApi.login` 或 `authApi.register`（`components/features/auth/login-form.tsx:22-38` / `register-form.tsx:23-39`）。
3. 成功后将 `access_token` 写入 `localStorage.token`（`login-form.tsx:29-31`）。
4. 跳转 `/home`（`login-form.tsx:31-32`）。
5. `(app)/home/layout` 加载时读取 token、调用 `authApi.me` 校验（`home/layout.tsx:35-57`）。
6. 校验通过后加载视频数量与会话列表（`home/layout.tsx:47-54`）。

### 流程2: 导入视频
1. 用户在 `/home` SmartInput 输入 B 站链接或点击“导入”意图（`home/page.tsx:75-87`）。
2. 触发 `importApi.singleAndProcess` 创建记录并立即调用 `/videos/{id}/process`（`videos.ts:58-66`）。
3. 导入成功后刷新首页数据并跳转 `/home/video/{id}`（`home/page.tsx:80-83`）。
4. 详情页调用 `videosApi.get`、`getTranscript` 获取基础信息与转写（`home/video/[id]/page.tsx:41-62`）。
5. 若状态未完成则启动轮询 `videosApi.getStatus` 直至 `done/failed`（`home/video/[id]/page.tsx:69-95`）。
6. 用户可在摘要/转写/评论 Tab 切换查看，并重新触发处理或导入评论分页（`home/video/[id]/page.tsx:203-317`）。

### 流程3: 知识库对话
1. 在 `/home` 点击“新对话”或选择历史对话（`Sidebar.tsx:91-121`）。
2. 若无当前对话，`useChat.sendMessageStream` 会先调用 `conversationsApi.create` 新建会话（`useChat.ts:163-176`）。
3. 用户在 ChatView/AliceInput 输入问题，可通过 @ 引用视频转写/对话上下文（`AliceInput.tsx:214-225`）。
4. `sendMessageStream` 使用 SSE 发送并逐步接收 `content`/`thinking` 事件（`useChat.ts:216-257`）。
5. 流式内容实时写入 UI（`ChatView/index.tsx:92-101` + `StreamingMessage.tsx:20-54`）。
6. 消息结束后刷新会话列表以更新标题与时间（`useChat.ts:245-254`）。

---

## 与后端接口的对应关系

### 接口调用映射表
| 前端页面/组件 | API 方法 | 后端端点 | 说明 |
|---------------|----------|----------|------|
| `/login` LoginForm (`components/features/auth/login-form.tsx:22-38`) | `authApi.login` | `/auth/login` | 登录并存储 token |
| `/register` RegisterForm (`components/features/auth/register-form.tsx:23-39`) | `authApi.register` | `/auth/register` | 注册并自动登录 |
| `(app)/home/layout` (`apps/web/src/app/(app)/home/layout.tsx:35-57`) | `authApi.me` | `/auth/me` | 登录校验，失败跳转登录 |
| `/home` Dashboard (`apps/web/src/app/(app)/home/page.tsx:35-56`) | `videosApi.list` | `/videos` | 获取最近视频与计数 |
| `/home` Dashboard (`apps/web/src/app/(app)/home/page.tsx:37-56`) | `authApi.me` | `/auth/me` | 获取用户名 |
| `/home` Dashboard (`apps/web/src/app/(app)/home/page.tsx:40-55`) | `videosApi.topTags` | `/videos/stats/tags` | 获取热门标签 |
| `/home` Dashboard (`apps/web/src/app/(app)/home/page.tsx:41-55`) | `suggestionsApi.get` | `/suggestions` | 获取灵感建议 |
| `/home` Chat (`apps/web/src/app/(app)/home/page.tsx:104-148`) | `sendMessageStream` | `/conversations/{id}/messages/stream` | SSE 对话 |
| `/home` Import (`apps/web/src/app/(app)/home/page.tsx:76-83`) | `importApi.singleAndProcess` | `/videos` + `/videos/{id}/process` | 导入并触发处理 |
| `/home/video/[id]` (`apps/web/src/app/(app)/home/video/[id]/page.tsx:41-125`) | `videosApi.get`/`getTranscript`/`getComments`/`getStatus` | `/videos/{id}` 等 | 详情、转写、评论、状态轮询 |
| `/home/library` (`apps/web/src/app/(app)/home/library/page.tsx:63-156`) | `videosApi.list` | `/videos` | 过滤/搜索视频 |
| `/home/library` (`apps/web/src/app/(app)/home/library/page.tsx:88-144`) | `bilibiliApi.getFolders` | `/bilibili/folders` | 读取收藏夹 |
| `/home/library` (`apps/web/src/app/(app)/home/library/page.tsx:134-144`) | `bilibiliApi.getFolderVideos` | `/bilibili/folders/{type}/{id}` | 收藏夹详情 |
| `/home/library` (`apps/web/src/app/(app)/home/library/page.tsx:106-125`) | `foldersApi.add` | `/folders` | 添加监控收藏夹 |
| `/home/library` (`apps/web/src/app/(app)/home/library/page.tsx:146-155`) | `importApi.single` | `/videos` | 单视频导入 |
| `/home/graph` (`apps/web/src/app/(app)/home/graph/page.tsx:22-57`) | `knowledgeApi.getGraph`/`getConceptVideos`/`getRelatedConcepts` | `/knowledge/*` | 图谱与相关数据 |
| `/home/settings` (`apps/web/src/app/(app)/home/settings/page.tsx:35-114`) | `foldersApi.list/delete` | `/folders` | 管理监控收藏夹 |
| `/home/settings` (`apps/web/src/app/(app)/home/settings/page.tsx:211-335`) | `configApi.updateASR` | `/config/asr` | 配置 ASR 提供商 |
| `/home/settings` (`apps/web/src/app/(app)/home/settings/page.tsx:337-511`) | `configApi.createLLMEndpoint`/`updateLLM` | `/config/llm/*` | LLM 端点与模型切换 |
| `/home/settings` (`apps/web/src/app/(app)/home/settings/page.tsx:1529-1781`) | `videosApi.getQueue/processNow/cancelProcess/removeFromQueue` | `/videos/queue/*` | 队列监控与操作 |
| `/home/settings` (`apps/web/src/app/(app)/home/settings/page.tsx:1784-1936`) | `systemApi.getStorage/cleanup` | `/system/*` | 存储统计与清理 |

---

## 发现的问题 / 待确认事项

### 🔴 严重问题
1. 旧路由未受鉴权保护
   - 位置: `apps/web/src/app/(app)/video/[id]/page.tsx`, `apps/web/src/app/(app)/library/page.tsx`, `apps/web/src/app/(app)/graph/page.tsx` 等占位页未通过 `(app)/home/layout` 包裹，缺少登录校验与 API 调用防护。
   - 影响: 用户可直接访问旧路径触发后端请求（若存在），绕过当前登录检查；未来可能暴露未完成页面。
   - 建议: 删除或重定向至 `/home/*` 对应页面，并在 `middleware`/布局统一校验。

2. 数据模型仍大量依赖 `bvid`
   - 位置: `apps/web/src/types/home.ts:3-22`、`home/video/[id]/page.tsx:174-247`、`VideoCard.tsx:91-165` 等直接使用 `bvid`。
   - 影响: 与架构规范“使用 source_type + source_id，不要用 bvid”冲突，后续支持多源时需要全面重构。
   - 建议: 前端类型与组件应切换为通用 `source_type/source_id` 字段，并在 API 层映射。

### 🟡 设计问题
- React Query Provider 未被实际使用
  - 位置: `apps/web/src/app/providers.tsx:6-21` 提供 QueryClient，但页面数据均通过 `useEffect` + axios；缓存与重试策略缺失。
  - 建议: 将列表/详情/配置请求迁移到 React Query，统一错误/加载状态。

- SSE 流式默认直连本地端口
  - 位置: `apps/web/src/lib/api/conversations.ts:22-77` 默认 `streamBaseUrl` 为 `http://localhost:8000`，需依赖 `NEXT_PUBLIC_API_STREAM_URL` 覆盖。
  - 影响: 部署环境若未设置变量会跨域失败；与 `/api/v1` 代理不一致。
  - 建议: 改为使用相对路径或从配置接口返回流式地址。

### 🟢 改进建议
- 统一错误提示：多数 API 调用 `catch` 后忽略错误（如 `home/page.tsx:35-62`、`library/page.tsx:80-97`），缺乏 UI 反馈。
- 安全信息隐藏：日志中 `console.error` 直接输出后端错误（`home/page.tsx:83-85`、`home/video/[id]/page.tsx:210-216`），需要过滤敏感字段。
- 组件分层：设置页文件过长（约 1900 行），可拆分为子模块与路由段以提升可维护性。
- 状态同步：`AliceInput` 单独拉取配置/视频列表，与 Dashboard/Settings 数据重复，可考虑将配置缓存到全局或 React Query。

---

## 附录

### A. 环境变量
- `NEXT_PUBLIC_API_STREAM_URL`：聊天 SSE 流地址，默认 `http://localhost:8000`（`conversations.ts:29-33`）。
- `localStorage.token`：前端持久化的 JWT，拦截器读取（`client.ts:14-21`）。

### B. 构建配置
- 脚本: `pnpm/yarn/npm run dev` → `next dev --turbopack`；`run build` → `next build`；`run start` → `next start`（`apps/web/package.json`）。
- Tailwind 4 + PostCSS 4，未见额外自定义配置文件。

### C. 开发命令
- 本地开发: `cd apps/web && npm run dev`
- 代码检查: `npm run lint`
- 生产构建: `npm run build`
