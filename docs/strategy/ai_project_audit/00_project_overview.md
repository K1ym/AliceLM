# 项目总览

**项目名称**: AliceLM (AI-powered Video Learning Manager)

**文档生成时间**: 2025-12-08

**数据来源**: 代码仓库静态分析

---

## 目录与模块一览

### 一级目录结构

```
alicelm/
├── alice/              # 🧠 核心平台库 (Agent引擎 + ControlPlane)
├── apps/               # 🖥️ 应用入口 (API后端 + Web前端 + MCP服务)
│   ├── api/            # FastAPI 后端服务
│   ├── web/            # Next.js 前端应用
│   └── mcp/            # MCP (Model Context Protocol) 服务端
├── services/           # ⚙️ 业务服务 (ASR/LLM/处理器/监控器)
│   ├── ai/             # AI 服务 (LLM管理、摘要、嵌入)
│   ├── asr/            # 语音识别服务
│   ├── downloader/     # 下载服务
│   ├── knowledge/      # 知识图谱服务
│   ├── processor/      # 视频处理流水线
│   ├── scheduler/      # 调度服务
│   └── watcher/        # 收藏夹监控服务
├── packages/           # 📦 共享基础包 (配置/数据库/日志/队列)
│   ├── config/         # 配置管理
│   ├── db/             # 数据库模型 & 连接
│   ├── queue/          # 任务队列 (占位，实际实现在 services/processor/queue.py)
│   ├── logging.py      # 日志工具
│   └── retry.py        # 重试机制
├── config/             # 🔧 YAML 配置文件
│   ├── base/           # 基础配置 (models/prompts/tools/services)
│   ├── dev/            # 开发环境覆盖
│   ├── prod/           # 生产环境覆盖
│   └── local/          # 本地覆盖 (gitignore)
├── codexmcp/           # 🔌 Codex MCP CLI 入口
├── docs/               # 📚 项目文档
├── tests/              # 🧪 测试套件
├── scripts/            # 🛠️ 运维脚本
├── bin/                # 可执行脚本
├── data/               # 📁 数据目录 (视频/音频/转写)
├── outputs/            # 输出目录
├── third_party/        # 第三方依赖
├── docker-compose.yml  # Docker 开发环境
├── docker-compose.prod.yml  # Docker 生产环境
├── Dockerfile          # Docker 镜像定义
├── pyproject.toml      # Python 项目配置
├── requirements.txt    # 依赖清单
└── uv.lock             # uv 锁文件
```

### 关键目录深入分析

#### 1. `alice/` - 核心平台库

| 子目录 | 功能描述 |
|--------|----------|
| `agent/` | Agent 执行引擎，包含策略选择、工具路由、MCP客户端、任务规划 |
| `control_plane/` | 控制平面，统一管理模型配置、提示词库、工具注册表、服务工厂 |
| `rag/` | RAG (检索增强生成) 服务集成 |
| `search/` | 搜索服务抽象层 (Tavily/DuckDuckGo/Mock) |
| `eval/` | Agent 评测框架 |
| `one/` | Alice One 高层业务封装 (IdentityService/ContextAssembler) |
| `errors.py` | 统一错误定义 |

#### 2. `apps/api/` - FastAPI 后端

| 子目录/文件 | 功能描述 |
|-------------|----------|
| `routers/` | API 路由 (13+ 模块) |
| `services/` | 业务服务层 |
| `repositories/` | 数据访问层 |
| `deps.py` | 依赖注入 |
| `main.py` | 应用入口 & 路由注册 |

#### 3. `apps/web/` - Next.js 前端

| 子目录 | 功能描述 |
|--------|----------|
| `src/app/` | App Router 页面 |
| `src/components/` | UI 组件库 (50+ 组件) |
| `src/hooks/` | 自定义 Hooks |
| `src/lib/` | 工具库 & API 客户端 |
| `src/types/` | TypeScript 类型定义 |

---

## 技术栈

### 后端 (Python 3.10+)

| 类别 | 技术选型 | 版本/说明 |
|------|----------|-----------|
| **Web框架** | FastAPI + Uvicorn | ≥0.104.0 |
| **ORM** | SQLAlchemy 2.0 | 声明式映射 |
| **数据库** | SQLite | 默认开发数据库 |
| **迁移** | Alembic | ≥1.12.0 |
| **任务调度** | APScheduler | ≥3.10.0 |
| **HTTP客户端** | httpx + requests | 异步 + 同步 |
| **配置管理** | PyYAML + python-dotenv | 分层配置 |
| **日志** | structlog | 结构化日志 |
| **验证** | Pydantic 2.5 + pydantic-settings | 数据校验 |

### AI/LLM 集成

| 类别 | 技术选型 | 说明 |
|------|----------|------|
| **LLM SDK** | OpenAI SDK + Anthropic SDK | 多端点支持 |
| **ASR** | Faster-Whisper / Groq Whisper / OpenAI Whisper | 语音转写 |
| **RAG** | Chroma / RAGFlow | 向量检索 |
| **Embedding** | text-embedding-3-large | OpenAI 嵌入模型 |
| **搜索** | Tavily / DuckDuckGo | Web 搜索 (Exa 仅 Agent 工具层实现) |
| **MCP** | mcp[cli] ≥1.20.0 | Model Context Protocol |

### 视频处理

| 类别 | 技术选型 | 说明 |
|------|----------|------|
| **下载** | you-get / BBDown / yt-dlp | 多平台视频下载 |
| **音视频处理** | moviepy + pydub + FFmpeg | 音频提取 |

### 认证/安全

| 类别 | 技术选型 |
|------|----------|
| **JWT** | python-jose[cryptography] |
| **密码哈希** | passlib[bcrypt] |

### 前端 (Node.js 20+)

| 类别 | 技术选型 | 版本 |
|------|----------|------|
| **框架** | Next.js | 15.1.0 (App Router + Turbopack) |
| **UI库** | React | 19.0.0 |
| **样式** | Tailwind CSS | 4.0.0 |
| **组件库** | Radix UI | 各种原语组件 |
| **状态管理** | React Hooks | useState/useRef (Zustand 已安装但未实际使用) |
| **数据请求** | TanStack React Query | 5.0.0 |
| **动画** | Framer Motion | 11.18.2 |
| **HTTP客户端** | Axios | 1.7.0 |
| **图标** | Lucide React + Tabler Icons | - |

### 开发与测试

| 类别 | 技术选型 |
|------|----------|
| **测试框架** | pytest + pytest-asyncio + pytest-cov |
| **代码检查** | Ruff |
| **类型检查** | mypy |
| **包管理** | uv (锁文件) |
| **构建系统** | Hatchling |

### 部署

| 类别 | 技术选型 |
|------|----------|
| **容器化** | Docker + Docker Compose |
| **编排** | docker-compose.prod.yml |

---

## 业务领域与核心目标

### 项目定位

**AliceLM** 是一个 **AI 驱动的视频知识库管理平台**，专注于将视频内容（主要来自 B站）转化为可检索、可对话的结构化知识。

### 核心功能

1. **视频转写** - 自动下载 B 站视频并使用 ASR 转写为文字
2. **AI 分析** - 提取核心要点、关键概念，生成结构化摘要
3. **智能问答** - 基于视频内容进行 AI 对话，支持引用上下文
4. **收藏夹监控** - 自动同步 B 站收藏夹，新视频自动处理
5. **多端点支持** - 支持 OpenAI、DeepSeek、Ollama 等多种 LLM
6. **MCP 服务** - 暴露搜索、摘要、问答工具给 Claude/GPT 等外部 AI 助手

### 核心业务流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                         视频入库流程                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  用户导入 / 收藏夹监控                                               │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────┐                                                    │
│  │ Video 记录  │ ← 元数据: source_type, source_id, title, author   │
│  └──────┬──────┘                                                    │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │               VideoProcessingQueue                       │        │
│  │  (全局线程池，限制并发，追踪状态)                          │        │
│  └──────────────────────┬──────────────────────────────────┘        │
│                         │                                           │
│                         ▼                                           │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │                   VideoPipeline                          │        │
│  │  下载 → 提取音频 → ASR转写 → AI摘要 → 向量化 → 通知       │        │
│  └──────────────────────┬──────────────────────────────────┘        │
│                         │                                           │
│                         ▼                                           │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │                    RAGService                            │        │
│  │  将转写内容上传到 Chroma/RAGFlow，支持语义检索            │        │
│  └─────────────────────────────────────────────────────────┘        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         知识消费流程                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   Web 前端   │    │  MCP Server  │    │  通知推送    │          │
│  │  Next.js UI  │    │ Claude/GPT   │    │  微信等      │          │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘          │
│         │                   │                                       │
│         └─────────┬─────────┘                                       │
│                   ▼                                                 │
│         ┌─────────────────────────────────────────┐                 │
│         │           FastAPI Backend               │                 │
│         │  /api/v1/qa/search  /api/v1/qa/ask     │                 │
│         │  /api/v1/videos  /api/v1/conversations │                 │
│         └─────────────────────────────────────────┘                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 目标用户角色

| 角色 | 描述 | 主要场景 |
|------|------|----------|
| **普通用户** | 知识学习者 | 导入视频、查看摘要、对话问答 |
| **管理员** | 租户管理者 | 配置 LLM/ASR、管理用户、查看统计 |
| **开发者** | 外部集成 | 通过 MCP 调用知识库工具 |
| **系统** | 自动化 | 收藏夹监控、定时处理、通知推送 |

---

## 主要模块/服务列表

### 后端模块

| 模块路径 | 类型 | 功能描述 |
|----------|------|----------|
| `apps/api/` | 后端服务 | FastAPI 主应用，提供 RESTful API |
| `apps/mcp/` | 后端服务 | MCP 服务端，暴露工具给外部 AI 助手 |
| `services/ai/` | 后端服务 | AI 服务集成 (LLM管理、摘要生成、嵌入) |
| `services/asr/` | 后端服务 | 语音识别服务 (多 Provider 支持) |
| `services/downloader/` | 后端服务 | 视频下载服务 (BBDown/yt-dlp) |
| `services/processor/` | 后端服务 | 视频处理流水线 (核心业务流程) |
| `services/watcher/` | 后端服务 | 收藏夹监控器 (定时扫描 + 触发处理) |
| `services/knowledge/` | 后端服务 | 知识图谱服务 |
| `services/scheduler/` | 后端服务 | 调度服务 |
| `services/notifier/` | 后端服务 | 通知服务 |

### 核心库模块

| 模块路径 | 类型 | 功能描述 |
|----------|------|----------|
| `alice/agent/` | 核心库 | Agent 执行引擎 (策略/工具/MCP客户端) |
| `alice/control_plane/` | 核心库 | 控制平面 (模型/提示词/工具注册表) |
| `alice/rag/` | 核心库 | RAG 服务抽象层 |
| `alice/search/` | 核心库 | 搜索服务抽象层 (Tavily/DuckDuckGo/Mock) |
| `alice/one/` | 核心库 | Alice One 高层封装 (IdentityService/ContextAssembler) |
| `packages/config/` | 公共包 | 分层配置管理 |
| `packages/db/` | 公共包 | 数据库模型 & 连接 |
| `packages/logging.py` | 公共包 | 结构化日志 |
| `packages/retry.py` | 公共包 | 重试机制 |

### 前端模块

| 模块路径 | 类型 | 功能描述 |
|----------|------|----------|
| `apps/web/` | 前端应用 | Next.js 15 + React 19 Web 界面 |
| `apps/web/src/app/(app)/` | 前端页面 | App Router 页面路由 |
| `apps/web/src/components/` | 前端组件 | UI 组件库 (50+ 组件) |

### 配置模块

| 模块路径 | 类型 | 功能描述 |
|----------|------|----------|
| `config/base/` | 配置 | 基础配置 (models/prompts/tools/services) |
| `config/dev/` | 配置 | 开发环境覆盖 |
| `config/prod/` | 配置 | 生产环境覆盖 |

### 脚本/工具

| 模块路径 | 类型 | 功能描述 |
|----------|------|----------|
| `codexmcp/` | CLI工具 | Codex MCP CLI 入口点 |
| `scripts/` | 脚本 | 运维脚本 |
| `tests/` | 测试 | pytest 测试套件 |

---

## 架构特征

### 整体架构模式

- **单体应用 + 前端分离**: 后端为单体 Python 应用，前端为独立 Next.js 应用
- **分层架构**: Router → Service → Repository → Model
- **配置驱动**: 通过 YAML 配置文件管理模型、工具、服务选择
- **插件化设计**: Provider 模式支持多种 ASR/LLM/搜索服务

### Agent 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AliceControlPlane (控制平面)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  ModelRegistry  │  │  PromptStore    │  │  ToolRegistry   │     │
│  │  模型配置注册    │  │  提示词模板库   │  │  工具注册表      │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐                          │
│  │  ServiceFactory │  │  LLMManager缓存 │                          │
│  │  服务实例工厂    │  │  按任务缓存实例  │                          │
│  └─────────────────┘  └─────────────────┘                          │
│                                                                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        AliceAgent (Agent引擎)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  core.py        │  │  strategy.py    │  │  tool_router.py │     │
│  │  Agent主循环    │  │  策略选择        │  │  工具路由        │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  mcp_client.py  │  │  task_planner   │  │  tool_executor  │     │
│  │  MCP客户端       │  │  任务规划        │  │  工具执行        │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 数据模型概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                          多租户系统                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Tenant (租户)                                                      │
│    │                                                                │
│    ├── User (用户)                                                  │
│    │     ├── UserPlatformBinding (平台绑定: Bilibili等)            │
│    │     ├── Conversation → Message (对话系统)                     │
│    │     └── LearningRecord (学习记录)                             │
│    │                                                                │
│    ├── Video (视频)                                                 │
│    │     └── VideoTag ←→ Tag (标签系统)                           │
│    │                                                                │
│    ├── WatchedFolder (监控收藏夹)                                   │
│    │                                                                │
│    ├── TenantConfig (租户配置)                                      │
│    │                                                                │
│    └── TimelineEvent (时间线事件)                                   │
│                                                                     │
│  AgentRun → AgentStep (Agent执行记录)                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 后续分析路线图

### Phase 1: 领域模型与核心业务流程 (优先级: 高)

**目标**: 深入理解数据模型和业务流程

**采集信息**:
- [ ] 完整的数据库 ER 图
- [ ] Video 状态机流转图
- [ ] 视频处理流水线详细步骤
- [ ] 多租户隔离机制

**产出文件**: `01_domain_model.md`

---

### Phase 2: API 接口与路由设计 (优先级: 高)

**目标**: 梳理所有 API 接口

**采集信息**:
- [ ] 所有 Router 的端点清单
- [ ] 请求/响应 Schema
- [ ] 认证/授权机制
- [ ] 错误处理规范

**产出文件**: `02_api_design.md`

---

### Phase 3: Agent 系统架构 (优先级: 高)

**目标**: 深入分析 Agent 引擎设计

**采集信息**:
- [ ] ControlPlane 配置加载流程
- [ ] Agent 执行主循环
- [ ] 工具注册与调用机制
- [ ] MCP 客户端集成
- [ ] 策略选择逻辑

**产出文件**: `03_agent_architecture.md`

---

### Phase 4: 前端页面与组件结构 (优先级: 中)

**目标**: 梳理前端架构

**采集信息**:
- [ ] App Router 页面结构
- [ ] 组件分类与层次
- [ ] 状态管理方案
- [ ] API 调用封装

**产出文件**: `04_frontend_architecture.md`

---

### Phase 5: 数据持久化与数据库结构 (优先级: 中)

**目标**: 详细分析数据层

**采集信息**:
- [ ] 完整的表结构定义
- [ ] 索引设计
- [ ] 迁移历史
- [ ] 数据访问模式

**产出文件**: `05_database_design.md`

---

### Phase 6: 外部系统集成 (优先级: 中)

**目标**: 分析第三方服务集成

**采集信息**:
- [ ] LLM Provider 集成 (OpenAI/DeepSeek/Ollama)
- [ ] ASR Provider 集成
- [ ] B站 API 集成
- [ ] RAG 服务集成 (Chroma/RAGFlow)
- [ ] 搜索服务集成

**产出文件**: `06_external_integrations.md`

---

### Phase 7: 配置与环境管理 (优先级: 中)

**目标**: 分析配置系统

**采集信息**:
- [ ] 分层配置加载顺序 (base → env → local → ENV)
- [ ] 所有配置项清单
- [ ] 环境变量映射
- [ ] Secret 管理

**产出文件**: `07_configuration.md`

---

### Phase 8: 部署与 CI/CD (优先级: 低)

**目标**: 分析部署流程

**采集信息**:
- [ ] Docker 镜像构建
- [ ] docker-compose 配置
- [ ] GitHub Actions 工作流
- [ ] 环境差异 (dev/prod)

**产出文件**: `08_deployment.md`

---

### Phase 9: 安全性与权限体系 (优先级: 低)

**目标**: 分析安全设计

**采集信息**:
- [ ] 认证流程 (JWT)
- [ ] 多租户权限模型
- [ ] API Key 管理
- [ ] 敏感数据处理

**产出文件**: `09_security.md`

---

## 代码与文档不一致之处

本节记录代码与 `docs/` 目录下文档的差异，**以代码为准**。

### 1. 多源重构尚未完成

| 文档要求 | 代码现状 |
|----------|----------|
| `docs/MULTI_SOURCE_REFACTOR.md` 及 `AGENTS.md` 要求彻底移除 `bvid` 字段，统一使用 `source_type` + `source_id` | `services/watcher/scanner.py` 仍使用 `video.bvid`；前端 `apps/web/src/app/(app)/home/library/page.tsx` 仍依赖 `bvid` 字段 |

**影响**: 多内容源扩展（YouTube、Podcast等）功能受阻

---

### 2. 前端状态管理方案

| 文档描述 | 代码现状 |
|----------|----------|
| `docs/FRONTEND_ARCHITECTURE.md:83-85` 提到 `stores/` 目录使用 Zustand | 实际不存在 `stores/` 目录，状态管理通过 `useChat` 等 Hook 内部 state 实现 |

**影响**: 文档指导与实际实现不符，可能导致开发者困惑

---

### 3. 占位页面

| 文档描述 | 代码现状 |
|----------|----------|
| `docs/PRD.md` 描述了 Graph/Timeline/TODO 等功能模块 | 代码中这些页面多为占位实现，功能未完整 |

**影响**: PRD 与实际完成度存在差距

---

### 4. Exa 搜索服务配置与实现不一致

| 配置描述 | 代码现状 |
|----------|----------|
| `config/base/services.yaml` 提到支持 Exa 搜索 | `alice/search/__init__.py` 仅暴露 Tavily、DuckDuckGo、Mock 三个 Provider；Exa 仅在 Agent 工具层 (`alice/agent/tools/ext/http_web.py`) 有部分实现 |

**影响**: 配置文件声明的能力与实际实现不匹配

---

### 5. packages/queue 目录为空

| 目录结构描述 | 代码现状 |
|--------------|----------|
| 一级目录结构图将 `packages/queue/` 描述为"任务队列" | 该目录仅包含空的 `__init__.py`，视频处理队列实际实现位于 `services/processor/queue.py` |

**影响**: 架构理解可能产生偏差

---

## 附录

### A. 主要配置文件清单

| 文件路径 | 用途 |
|----------|------|
| `config/base/models.yaml` | 模型 Profile 定义 (Chat/Embedding/ASR) |
| `config/base/prompts.yaml` | 提示词模板库 |
| `config/base/tools.yaml` | 工具配置与场景绑定 |
| `config/base/services.yaml` | 服务 Provider 选择 |
| `config/base/default.yaml` | 默认应用配置 |

### B. API 路由列表

| 前缀 | 模块 | 功能 |
|------|------|------|
| `/api/v1/auth` | 认证 | 登录/注册/令牌 |
| `/api/v1/videos` | 视频 | CRUD/处理/导入 |
| `/api/v1/folders` | 收藏夹 | 监控管理 |
| `/api/v1/qa` | 问答 | 搜索/问答 |
| `/api/v1/knowledge` | 知识图谱 | 图谱操作 |
| `/api/v1/config` | 配置 | 用户/租户配置 |
| `/api/v1/bilibili` | B站绑定 | 账号绑定 |
| `/api/v1/conversations` | 对话 | 对话管理 |
| `/api/v1/system` | 系统 | 系统管理 |
| `/api/v1/suggestions` | 灵感 | 建议推荐 |
| `/api/v1/agent` | Agent | Agent 调用 |
| `/api/v1/console` | Console | 控制台 |
| `/api/v1/control-plane` | ControlPlane | 控制平面管理 |

### C. 数据库模型列表

| 模型 | 说明 |
|------|------|
| `Tenant` | 租户/组织 |
| `User` | 用户 |
| `UserPlatformBinding` | 用户平台绑定 |
| `TenantConfig` | 租户配置 |
| `UserConfig` | 用户配置 |
| `Video` | 视频 |
| `Tag` | 标签 |
| `VideoTag` | 视频-标签关联 |
| `WatchedFolder` | 监控收藏夹 |
| `LearningRecord` | 学习记录 |
| `TimelineEvent` | 时间线事件 |
| `AgentRun` | Agent 运行记录 |
| `AgentStep` | Agent 执行步骤 |
| `Conversation` | 对话 |
| `Message` | 消息 |

---

*本文档由 AI 自动生成，基于代码仓库静态分析，建议结合实际代码阅读理解。*
