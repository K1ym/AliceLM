# 领域模型与核心业务流程

**文档生成时间**: 2025-12-08

**数据来源**: 代码仓库静态分析 (以代码为准)

---

## 核心领域模型一览

### 1. 枚举类型

| 枚举名 | 文件路径 | 用途 | 取值 |
|--------|----------|------|------|
| `TenantPlan` | `packages/db/models.py:29-34` | 租户订阅计划 | `FREE`, `PRO`, `TEAM`, `ENTERPRISE` |
| `UserRole` | `packages/db/models.py:37-42` | 用户角色 | `OWNER`, `ADMIN`, `MEMBER`, `VIEWER` |
| `VideoStatus` | `packages/db/models.py:45-53` | 视频处理状态 | `PENDING`, `DOWNLOADING`, `TRANSCRIBING`, `ANALYZING`, `INDEXING`, `DONE`, `FAILED` |
| `EventType` | `packages/db/models.py:302-330` | 时间线事件类型 | 视频/问答/学习/报告/知识图谱/Agent/系统相关事件 |
| `SceneType` | `packages/db/models.py:333-345` | 事件发生场景 | `CHAT`, `LIBRARY`, `VIDEO`, `GRAPH`, `TIMELINE`, `TASKS`, `CONSOLE`, `SETTINGS`, `WECHAT`, `MCP`, `SYSTEM` |
| `AgentRunStatus` | `packages/db/models.py:384-389` | Agent运行状态 | `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED` |
| `MessageRole` | `packages/db/models.py:447-451` | 消息角色 | `USER`, `ASSISTANT`, `SYSTEM` |

---

### 2. 核心实体模型

#### 2.1 多租户与用户系统

##### Tenant (租户/组织)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `name` | String(100) | ✅ | 租户名称 |
| `slug` | String(50) | ✅ | URL友好的唯一标识 (唯一索引) |
| `plan` | Enum(TenantPlan) | ✅ | 订阅计划 (默认 FREE) |
| `plan_expires_at` | DateTime | ❌ | 计划过期时间 |
| `max_videos` | Integer | ✅ | 最大视频数 (默认 100) |
| `max_storage_gb` | Integer | ✅ | 最大存储 GB (默认 10) |
| `max_users` | Integer | ✅ | 最大用户数 (默认 1) |
| `is_active` | Boolean | ✅ | 是否激活 (默认 True) |
| `created_at` | DateTime | ✅ | 创建时间 |

**文件路径**: `packages/db/models.py:58-85`

---

##### User (用户)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `tenant_id` | Integer (FK) | ✅ | 所属租户 |
| `email` | String(255) | ✅ | 邮箱 (唯一索引) |
| `username` | String(50) | ✅ | 用户名 |
| `password_hash` | String(255) | ❌ | 密码哈希 (bcrypt) |
| `wechat_openid` | String(100) | ❌ | 微信 OpenID (旧字段) |
| `role` | Enum(UserRole) | ✅ | 角色 (默认 MEMBER) |
| `is_active` | Boolean | ✅ | 是否激活 |
| `last_login_at` | DateTime | ❌ | 最后登录时间 |
| `created_at` | DateTime | ✅ | 创建时间 |

**文件路径**: `packages/db/models.py:88-121`

---

##### UserPlatformBinding (用户平台绑定)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `user_id` | Integer (FK) | ✅ | 所属用户 |
| `platform` | String(20) | ✅ | 平台类型 (`bilibili`/`youtube`/`podcast`) |
| `platform_uid` | String(100) | ✅ | 平台用户ID |
| `credentials` | Text | ❌ | JSON 凭证 (token/sessdata) |
| `is_active` | Boolean | ✅ | 是否激活 |
| `created_at` | DateTime | ✅ | 创建时间 |

**唯一约束**: `(user_id, platform)`

**文件路径**: `packages/db/models.py:124-143`

---

#### 2.2 视频与知识系统

##### Video (视频) ⭐ 核心聚合根

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `tenant_id` | Integer (FK) | ✅ | 所属租户 |
| `watched_folder_id` | Integer (FK) | ❌ | 来源收藏夹 |
| `source_type` | String(20) | ✅ | 内容源类型 (默认 `bilibili`) |
| `source_id` | String(100) | ✅ | 源ID (bvid/youtube_id/rss_guid) |
| `source_url` | String(500) | ❌ | 源URL |
| `title` | String(500) | ✅ | 标题 |
| `author` | String(100) | ✅ | 作者 |
| `duration` | Integer | ✅ | 时长(秒) |
| `cover_url` | String(500) | ❌ | 封面URL |
| `status` | String(20) | ✅ | 处理状态 (存储枚举值) |
| `error_message` | Text | ❌ | 错误信息 |
| `retry_count` | Integer | ✅ | 重试次数 |
| `video_path` | String(500) | ❌ | 视频文件路径 |
| `audio_path` | String(500) | ❌ | 音频文件路径 |
| `transcript_path` | String(500) | ❌ | 转写文件路径 |
| `summary` | Text | ❌ | AI 生成摘要 |
| `key_points` | Text | ❌ | AI 生成要点 (JSON) |
| `concepts` | Text | ❌ | AI 生成概念 (JSON) |
| `asr_provider` | String(50) | ❌ | ASR 提供商 |
| `llm_provider` | String(50) | ❌ | LLM 提供商 |
| `collected_at` | DateTime | ❌ | 收集时间 |
| `processed_at` | DateTime | ❌ | 处理完成时间 |
| `created_at` | DateTime | ✅ | 创建时间 |
| `updated_at` | DateTime | ❌ | 更新时间 |

**唯一约束**: `(tenant_id, source_type, source_id)`

**索引**: `(tenant_id, status)`, `(tenant_id, source_type)`

**文件路径**: `packages/db/models.py:176-233`

---

##### Tag (标签)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `name` | String(50) | ✅ | 标签名 (唯一) |
| `category` | String(50) | ❌ | 标签分类 |

**文件路径**: `packages/db/models.py:236-244`

---

##### VideoTag (视频-标签关联)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `video_id` | Integer (PK, FK) | ✅ | 视频ID |
| `tag_id` | Integer (PK, FK) | ✅ | 标签ID |
| `confidence` | Float | ✅ | 置信度 (默认 1.0) |

**文件路径**: `packages/db/models.py:247-256`

---

##### WatchedFolder (监控收藏夹)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `tenant_id` | Integer (FK) | ✅ | 所属租户 |
| `folder_id` | String(50) | ✅ | 收藏夹ID |
| `folder_type` | String(20) | ✅ | 类型 (`favlist`/`season`/`subscription`) |
| `name` | String(200) | ✅ | 收藏夹名称 |
| `platform` | String(20) | ✅ | 平台 (默认 `bilibili`) |
| `last_scan_at` | DateTime | ❌ | 最后扫描时间 |
| `is_active` | Boolean | ✅ | 是否激活 |

**唯一约束**: `(tenant_id, folder_id)`

**文件路径**: `packages/db/models.py:261-280`

---

#### 2.3 对话与问答系统

##### Conversation (对话)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `tenant_id` | Integer (FK) | ✅ | 所属租户 |
| `user_id` | Integer (FK) | ✅ | 所属用户 |
| `title` | String(200) | ❌ | 对话标题 (从首条消息生成) |
| `compressed_context` | Text | ❌ | 压缩后的历史摘要 |
| `compressed_at_message_id` | Integer | ❌ | 压缩到哪条消息 |
| `created_at` | DateTime | ✅ | 创建时间 |
| `updated_at` | DateTime | ✅ | 更新时间 |

**文件路径**: `packages/db/models.py:454-477`

---

##### Message (消息)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `conversation_id` | Integer (FK) | ✅ | 所属对话 |
| `role` | Enum(MessageRole) | ✅ | 角色 |
| `content` | Text | ✅ | 消息内容 |
| `sources` | Text | ❌ | RAG 检索来源 (JSON) |
| `created_at` | DateTime | ✅ | 创建时间 |

**文件路径**: `packages/db/models.py:480-500`

---

#### 2.4 Agent 执行系统

##### AgentRun (Agent运行记录)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `tenant_id` | Integer (FK) | ✅ | 所属租户 |
| `user_id` | Integer (FK) | ❌ | 触发用户 |
| `scene` | String(50) | ✅ | 执行场景 |
| `query` | Text | ✅ | 用户查询 |
| `strategy` | String(50) | ❌ | 执行策略 |
| `status` | Enum(AgentRunStatus) | ✅ | 运行状态 |
| `answer` | Text | ❌ | 回答结果 |
| `citations` | Text | ❌ | 引用 (JSON) |
| `error` | Text | ❌ | 错误信息 |
| `prompt_tokens` | Integer | ❌ | Prompt Token 数 |
| `completion_tokens` | Integer | ❌ | Completion Token 数 |
| `created_at` | DateTime | ✅ | 创建时间 |
| `completed_at` | DateTime | ❌ | 完成时间 |

**文件路径**: `packages/db/models.py:392-422`

---

##### AgentStep (Agent执行步骤)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `run_id` | Integer (FK) | ✅ | 所属运行记录 |
| `step_idx` | Integer | ✅ | 步骤序号 |
| `thought` | Text | ❌ | 思考过程 |
| `tool_name` | String(100) | ❌ | 工具名称 |
| `tool_args` | Text | ❌ | 工具参数 (JSON) |
| `observation` | Text | ❌ | 观察结果 |
| `error` | Text | ❌ | 错误信息 |
| `created_at` | DateTime | ✅ | 创建时间 |

**文件路径**: `packages/db/models.py:425-442`

---

#### 2.5 时间线与遥测

##### TimelineEvent (时间线事件)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `tenant_id` | Integer (FK) | ✅ | 所属租户 |
| `user_id` | Integer (FK) | ❌ | 关联用户 |
| `event_type` | Enum(EventType) | ✅ | 事件类型 |
| `scene` | Enum(SceneType) | ✅ | 事件场景 |
| `video_id` | Integer (FK) | ❌ | 关联视频 |
| `conversation_id` | Integer (FK) | ❌ | 关联对话 |
| `title` | String(200) | ❌ | 事件简述 |
| `context` | Text | ❌ | 详细上下文 (JSON) |
| `created_at` | DateTime | ✅ | 创建时间 |

**索引**: `(tenant_id, user_id, created_at)`, `(tenant_id, event_type, created_at)`

**文件路径**: `packages/db/models.py:348-379`

---

##### LearningRecord (学习记录 - 兼容旧表)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `tenant_id` | Integer (FK) | ✅ | 所属租户 |
| `user_id` | Integer (FK) | ✅ | 用户 |
| `video_id` | Integer (FK) | ✅ | 视频 |
| `action` | String(20) | ✅ | 行为 (`viewed`/`asked`/`reviewed`/`exported`) |
| `duration` | Integer | ❌ | 时长 |
| `created_at` | DateTime | ✅ | 创建时间 |
| `extra_data` | Text | ❌ | 额外数据 (JSON) |

**文件路径**: `packages/db/models.py:283-297`

---

#### 2.6 配置系统

##### TenantConfig (租户配置)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `tenant_id` | Integer (FK) | ✅ | 所属租户 |
| `key` | String(100) | ✅ | 配置键 |
| `value` | Text | ✅ | 配置值 |

**唯一约束**: `(tenant_id, key)`

**文件路径**: `packages/db/models.py:146-158`

---

##### UserConfig (用户配置)

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `id` | Integer | ✅ | 主键 |
| `user_id` | Integer (FK) | ✅ | 所属用户 |
| `key` | String(100) | ✅ | 配置键 |
| `value` | Text | ✅ | 配置值 |

**唯一约束**: `(user_id, key)`

**文件路径**: `packages/db/models.py:161-171`

---

## 模型关系图

### 实体关系描述

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              多租户核心                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Tenant ──────┬──────── 1:N ────────── User                                │
│     │         │                          │                                  │
│     │         └──── 1:N ──── TenantConfig                                  │
│     │                                    │                                  │
│     │                                    └──── 1:N ──── UserPlatformBinding│
│     │                                    └──── 1:N ──── UserConfig         │
│     │                                    └──── 1:N ──── Conversation       │
│     │                                    └──── 1:N ──── LearningRecord     │
│     │                                                                       │
│     ├──────── 1:N ────────── Video ─────┬──── N:M ──── Tag (via VideoTag)  │
│     │                          │        │                                   │
│     │                          │        └──── 1:N ──── TimelineEvent       │
│     │                          │                                            │
│     ├──────── 1:N ──── WatchedFolder ───┴──── 1:N ──── Video               │
│     │                                                                       │
│     └──────── 1:N ──── TimelineEvent                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              对话系统                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User ──────── 1:N ──────── Conversation ──────── 1:N ──────── Message     │
│                                   │                                         │
│                                   └──── 关联 ──── TimelineEvent             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent 执行系统                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Tenant ──┬── 1:N ──── AgentRun ──────── 1:N ──────── AgentStep            │
│           │               │                                                 │
│  User ────┴── 0:N ────────┘                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 关系列表

| 源实体 | 关系类型 | 目标实体 | 外键 | 说明 |
|--------|----------|----------|------|------|
| Tenant | 1:N | User | `users.tenant_id` | 租户下多用户 |
| Tenant | 1:N | Video | `videos.tenant_id` | 租户下多视频 |
| Tenant | 1:N | TenantConfig | `tenant_configs.tenant_id` | 租户配置 |
| Tenant | 1:N | WatchedFolder | `watched_folders.tenant_id` | 监控收藏夹 |
| User | 1:N | UserPlatformBinding | `user_platform_bindings.user_id` | 平台绑定 |
| User | 1:N | Conversation | `conversations.user_id` | 用户对话 |
| User | 1:N | LearningRecord | `learning_records.user_id` | 学习记录 |
| WatchedFolder | 1:N | Video | `videos.watched_folder_id` | 收藏夹视频 |
| Video | N:M | Tag | `video_tags` (Junction) | 视频标签 |
| Conversation | 1:N | Message | `messages.conversation_id` | 对话消息 |
| AgentRun | 1:N | AgentStep | `agent_steps.run_id` | Agent 步骤 |
| Tenant | 1:N | TimelineEvent | `timeline_events.tenant_id` | 时间线事件 |
| Tenant | 1:N | AgentRun | `agent_runs.tenant_id` | Agent 运行记录 |
| Tenant | 1:N | LearningRecord | `learning_records.tenant_id` | 学习记录 |
| User | 0:N | TimelineEvent | `timeline_events.user_id` | 用户时间线 |
| User | 0:N | AgentRun | `agent_runs.user_id` | 用户 Agent 记录 |
| Video | 1:N | TimelineEvent | `timeline_events.video_id` | 视频时间线 |
| Video | 1:N | LearningRecord | `learning_records.video_id` | 视频学习记录 |

---

## 核心业务流程

### Flow-1: 视频导入与处理流程 ⭐

**触发入口**: 
- API: `POST /api/v1/videos/import`
- 代码: `apps/api/routers/videos.py:50-109`

**状态机流转**:

```
                  ┌──────────────────────────────────────────────────────────┐
                  │                    VideoStatus 状态机                     │
                  └──────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────┐  导入  ┌─────────┐  下载  ┌─────────────┐  ASR  ┌─────────────┐
│  (新建)  │──────▶│ PENDING │──────▶│ DOWNLOADING │──────▶│TRANSCRIBING │
└─────────┘       └────┬────┘       └──────┬──────┘       └──────┬──────┘
                       │                   │                     │
                       │                   ▼                     ▼
                       │              ┌─────────┐           ┌───────────┐
                       │              │ FAILED  │◀─ error ──│ ANALYZING │
                       │              └────┬────┘           └─────┬─────┘
                       │                   │                      │
                       │                   ▼                      ▼
                       │     reset    ┌─────────┐  索引    ┌──────────┐
                       └─────────────▶│ PENDING │◀────────│ INDEXING │
                                      └─────────┘          └────┬─────┘
                                                                │
                                                                ▼
                                                          ┌──────────┐
                                                          │   DONE   │
                                                          └──────────┘
```

**详细步骤**:

| 步骤 | 执行组件 | 操作 | 状态变化 |
|------|----------|------|----------|
| 1 | `VideoService.import_video()` | 解析 BV 号、获取视频信息、创建 Video 记录 | → `PENDING` |
| 2 | `VideoProcessingQueue.submit()` | 加入处理队列，分配线程池 worker | `PENDING` → `DOWNLOADING` |
| 3 | `VideoPipeline.process()` | 下载视频 (BBDown/yt-dlp) | `DOWNLOADING` |
| 4 | `AudioProcessor.extract()` | 提取音频 → audio_path | `DOWNLOADING` |
| 5 | `ASRManager.transcribe()` | 语音转文字 → transcript_path | → `TRANSCRIBING` |
| 6 | `Summarizer.analyze()` | AI 摘要/要点/概念提取，写入 summary/key_points/concepts | → `ANALYZING` |
| 7 | `RAGService.index()` | 向量化并索引到 Chroma | → `INDEXING` |
| 8 | 更新 Video 记录 | 设置 processed_at，完成处理 | → `DONE` |

**涉及文件**:
- `apps/api/services/video_service.py:45-81`
- `services/processor/queue.py:73-128`
- `services/processor/pipeline.py:92-278`

---

### Flow-2: 用户认证流程

**触发入口**:
- 登录: `POST /api/v1/auth/login`
- 注册: `POST /api/v1/auth/register`
- 代码: `apps/api/routers/auth.py:44-76`

**详细步骤**:

#### 2.1 用户注册

| 步骤 | 执行组件 | 操作 |
|------|----------|------|
| 1 | `auth.register()` | 接收 email/username/password |
| 2 | `AuthService.email_exists()` | 检查邮箱是否已注册 |
| 3 | `AuthService.register()` | 创建 Tenant + User + 密码哈希 |
| 4 | `create_access_token()` | 生成 JWT Token (24h 有效期) |
| 5 | 返回 TokenResponse | `{access_token, expires_in}` |

#### 2.2 用户登录

| 步骤 | 执行组件 | 操作 |
|------|----------|------|
| 1 | `auth.login()` | 接收 email/password |
| 2 | `AuthService.authenticate()` | 验证密码 (bcrypt) |
| 3 | `create_access_token()` | 生成 JWT Token |
| 4 | 返回 TokenResponse | `{access_token, expires_in}` |

**涉及文件**:
- `apps/api/routers/auth.py:28-76`
- `apps/api/services/auth_service.py:46-103`

---

### Flow-3: 智能对话流程

**触发入口**:
- API: `POST /api/v1/conversations/{conversation_id}/messages/stream` (SSE 流式)
- 代码: `apps/api/routers/conversations.py:185-323`

**详细步骤**:

| 步骤 | 执行组件 | 操作 |
|------|----------|------|
| 1 | `send_message_stream()` | 接收用户消息 |
| 2 | `ChatService` | 保存用户消息到 Message 表 |
| 3 | 历史检查 | 判断是否需要上下文压缩 (>20k字符) |
| 4 | `RAGService.search()` | 语义检索相关视频片段 |
| 5 | `ControlPlane` | 获取 LLM 配置 |
| 6 | `LLMManager.chat_stream()` | 流式生成回答 |
| 7 | SSE 推送 | 逐 chunk 返回内容 |
| 8 | 保存 AI 消息 | 写入 Message 表 (含 sources) |
| 9 | 更新对话 | 更新 conversation.updated_at |

**涉及文件**:
- `apps/api/routers/conversations.py:185-323`
- `apps/api/services/chat_service.py`
- `services/ai/llm/manager.py`

---

### Flow-4: 收藏夹监控流程

**触发入口**:
- 定时任务 / 手动扫描
- 代码: `services/watcher/scanner.py:33-101`

**详细步骤**:

| 步骤 | 执行组件 | 操作 |
|------|----------|------|
| 1 | `FolderScanner.scan_all_folders()` | 查询所有激活的 WatchedFolder |
| 2 | `BilibiliClient.fetch_favlist()` | 获取收藏夹视频列表 |
| 3 | 去重检查 | 查询 `(tenant_id, source_id)` 是否已存在 |
| 4 | 创建 Video | 设置 `status=PENDING`, 关联 folder |
| 5 | 更新 folder | 更新 `last_scan_at` |
| 6 | ⏳ 等待 | 新视频等待后续调度任务或手动触发处理 |

> ⚠️ **注意**: `FolderScanner` 只创建 Video 记录，不直接加入 `VideoProcessingQueue`。处理队列需要通过定时任务 (`process_pending`) 或手动触发 (`/videos/{id}/process`) 启动。

**涉及文件**:
- `services/watcher/scanner.py:33-134`
- `services/watcher/bilibili.py`
- `apps/api/services/folder_service.py:42-115`

---

### Flow-5: 知识问答流程

**触发入口**:
- API: `POST /api/v1/qa/ask`
- 代码: `apps/api/routers/qa.py:42-87`

**详细步骤**:

| 步骤 | 执行组件 | 操作 |
|------|----------|------|
| 1 | `ask_question()` | 接收问题和可选的 video_ids |
| 2 | `RAGService.is_available()` | 检查向量服务可用性 |
| 3 | (降级) `FallbackRAGService` | 若不可用则使用数据库 LIKE 搜索 |
| 4 | `RAGService.ask()` | 检索相关片段 + LLM 生成回答 |
| 5 | 构造响应 | 返回 answer + sources |

**涉及文件**:
- `apps/api/routers/qa.py:42-87`
- `alice/rag/service.py`

---

## 关键业务规则与校验逻辑

### 1. 数据唯一性约束

| 规则 | 约束 | 文件位置 |
|------|------|----------|
| 租户内视频唯一 | `UNIQUE(tenant_id, source_type, source_id)` | `models.py:230` |
| 用户邮箱唯一 | `UNIQUE(email)` | `models.py:96` |
| 租户 slug 唯一 | `UNIQUE(slug)` | `models.py:64` |
| 用户平台绑定唯一 | `UNIQUE(user_id, platform)` | `models.py:142` |
| 租户配置唯一 | `UNIQUE(tenant_id, key)` | `models.py:158` |
| 收藏夹唯一 | `UNIQUE(tenant_id, folder_id)` | `models.py:280` |

---

### 2. 视频处理规则

| 规则 | 位置 | 说明 |
|------|------|------|
| BV 号格式校验 | `video_service.py:24-43` | 必须匹配 `/BV[a-zA-Z0-9]+/` |
| 批量导入上限 | `videos.py:80` | 单次最多 20 条 |
| 并行处理限制 | `queue.py:17` | `MAX_PARALLEL_VIDEOS = 2` |
| 重复任务拒绝 | `queue.py:82-86` | 已在 queued/running 状态的视频不可重复提交 |
| 重试条件 | `video_service.py:161-168` | 仅 `FAILED` 状态可重试 |
| 手动处理条件 | `videos.py:382-400` | 仅 `pending/failed` 状态可手动触发 |
| 状态枚举校验 | `videos.py:121-137` | 列表 API 会将 status 参数转为 VideoStatus 枚举，非法值抛 ValidationException |
| 转写文件检查 | `videos.py:264-300` | 获取转写前检查 `transcript_path` 字段和文件是否存在 |
| 队列取消条件 | `videos.py:436-477` | 取消/删除队列任务仅限 pending/failed 状态 |

---

### 3. 认证与授权规则

| 规则 | 位置 | 说明 |
|------|------|------|
| JWT 有效期 | `auth.py:25` | 24 小时 |
| 密码哈希 | `auth_service.py` | bcrypt |
| Debug 模式降级 | `deps.py:36-88` | 无 token 时使用 `admin@local` |
| 收藏夹需绑定 | `folder_service.py:42-84` | 必须有 SESSDATA 才能添加 |

---

### 4. 服务降级规则

| 规则 | 位置 | 说明 |
|------|------|------|
| RAG 服务降级 | `qa.py:53-57` | 不可用时使用 FallbackRAGService |
| ASR 降级 | `pipeline.py:48-80` | 通过 ControlPlane 配置 fallback |

---

### 5. 多租户隔离

| 规则 | 位置 | 说明 |
|------|------|------|
| 数据隔离 | 所有查询 | 必须带 `tenant_id` 过滤 |
| 配额限制 | `models.py:70-73` | ⚠️ 仅定义未强制 (max_videos/storage/users) |

---

## 发现的问题 / 模糊点

### 🔴 严重问题

#### 1. 枚举值不一致 - `VideoStatus.IMPORTED`

| 问题 | 代码使用 `VideoStatus.IMPORTED` (`video_service.py:77`) 但枚举未定义此值 |
|------|---------------------------------------------------------------|
| 位置 | `apps/api/services/video_service.py:77` vs `packages/db/models.py:45-53` |
| 影响 | `auto_process=False` 场景会抛出运行时错误 |
| 建议 | 在 `VideoStatus` 枚举中添加 `IMPORTED = "imported"` |

---

#### 2. 多源重构未完成 - `bvid` 字段

| 问题 | `scanner.py` 仍使用 `bvid=video_info.source_id` 但模型只有 `source_id` |
|------|---------------------------------------------------------------|
| 位置 | `services/watcher/scanner.py:65-77` |
| 影响 | 创建视频时可能抛出 `TypeError`；违反 AGENTS.md 约定 |
| 建议 | 改为 `source_id=video_info.source_id` |

---

#### 3. VideoPipeline 仍引用 `bvid` 变量

| 问题 | `_save_transcript()` 日志引用未定义的 `bvid` 变量 |
|------|---------------------------------------------------------------|
| 位置 | `services/processor/pipeline.py:310-339` |
| 影响 | 转写保存时可能抛出 `NameError` |
| 建议 | 更换为 `source_id` |

---

### 🟡 中等问题

#### 4. 配额未强制执行

| 问题 | `Tenant.max_videos/max_storage_gb/max_users` 未在导入/注册路径校验 |
|------|---------------------------------------------------------------|
| 位置 | `packages/db/models.py:70-73` |
| 影响 | 用户可无限导入视频，超出订阅计划限制 |
| 建议 | 在 `VideoService.import_video()` 和 `AuthService.register()` 添加配额检查 |

---

#### 5. 角色权限未实现

| 问题 | `UserRole` (OWNER/ADMIN/MEMBER/VIEWER) 仅定义未使用 |
|------|---------------------------------------------------------------|
| 位置 | `packages/db/models.py:37-42` |
| 影响 | 所有用户权限相同，无法实现精细权限控制 |
| 建议 | 在 router 层添加 role-based 权限检查 |

---

### 🟢 规划但未完成

| 功能 | 状态 | 说明 |
|------|------|------|
| Timeline 系统 | 模型已定义 | `TimelineEvent` 事件记录尚未在业务层写入 |
| 知识图谱 | 路由存在 | 具体功能为占位实现 |
| 上下文压缩 | 字段存在 | `compressed_context` 压缩逻辑在路由中有阈值判断但实现不完整 |

---

*本文档由 AI 自动生成，基于代码仓库静态分析，建议结合实际代码阅读理解。*
