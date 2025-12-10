# 🏗️ AliceLM 技术设计文档

---

## 1. 设计原则

### 1.1 核心原则

| 原则 | 说明 | 实践 |
|------|------|------|
| **模块化** | 功能解耦，独立演进 | 插件式ASR/LLM/Notifier |
| **可扩展** | 面向接口，易于扩展 | Provider抽象层 |
| **多租户** | 支持多用户隔离 | Tenant-aware数据模型 |
| **数据分层** | 结构化+向量化分离 | SQL + VectorDB |
| **配置驱动** | 行为可配置，无需改代码 | YAML/ENV配置 |

### 1.2 扩展性设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      Plugin Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Source Plugins │  │   ASR Plugins   │  │   LLM Plugins   │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤ │
│  │ • Bilibili      │  │ • Whisper       │  │ • OpenAI        │ │
│  │ • YouTube       │  │ • Faster-Whisper│  │ • Claude        │ │
│  │ • Podcast       │  │ • 讯飞          │  │ • Ollama(本地)  │ │
│  │ • Local File    │  │ • 阿里          │  │ • DeepSeek      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│           │                   │                   │             │
│           ▼                   ▼                   ▼             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Core Engine (Provider Interface)               ││
│  └─────────────────────────────────────────────────────────────┘│
│           │                   │                   │             │
│           ▼                   ▼                   ▼             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Notify Plugins  │  │  Store Plugins  │  │ Export Plugins  │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤ │
│  │ • 企业微信      │  │ • SQLite        │  │ • Markdown      │ │
│  │ • Telegram      │  │ • PostgreSQL    │  │ • Notion        │ │
│  │ • 邮件          │  │ • MySQL         │  │ • Obsidian      │ │
│  │ • Webhook       │  │ • MongoDB       │  │ • Anki          │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 系统架构

### 2.1 整体架构（多租户）

```
┌─────────────────────────────────────────────────────────────────┐
│                        Clients                                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ 微信Bot  │  │  Web UI  │  │   MCP    │  │  CLI     │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
└───────┼─────────────┼─────────────┼─────────────┼───────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway + Auth                          │
│                   (FastAPI + JWT/OAuth)                         │
├─────────────────────────────────────────────────────────────────┤
│  • 认证/授权    • 租户识别    • 限流    • 日志                   │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Service Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  Alice One + Agent Engine                   ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐││
│  │  │AliceIdentity│ │ContextAssem │ │    AliceAgentCore       │││
│  │  │  Service    │ │   bler      │ │ (Strategy/Planner/Exec) │││
│  │  └─────────────┘ └─────────────┘ └─────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │  Watcher  │ │ Processor │ │ Knowledge │ │  Notifier │       │
│  │  Service  │ │  Service  │ │  Service  │ │  Service  │       │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘       │
│        │             │             │             │              │
│        ▼             ▼             ▼             ▼              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Provider Layer (Pluggable)                     ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │  SourceProvider │ ASRProvider │ LLMProvider │ RAGProvider  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Task Queue Layer                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐│
│  │           Redis / APScheduler (Per-Tenant Queue)            ││
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    ││
│  │  │download│ │  asr   │ │analyze │ │ embed  │ │ notify │    ││
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  Relational DB (Per-Tenant)                 ││
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    ││
│  │  │ users  │ │ videos │ │  tags  │ │configs │ │ logs   │    ││
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    ││
│  │          SQLite (单机) / PostgreSQL (生产)                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  Vector DB (Per-Tenant)                     ││
│  │  ┌────────────────┐  ┌────────────────┐                     ││
│  │  │  embeddings    │  │   indexes      │                     ││
│  │  │  (chunks)      │  │  (HNSW/IVF)    │                     ││
│  │  └────────────────┘  └────────────────┘                     ││
│  │          ChromaDB (单机) / Qdrant/Milvus (生产)              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  File Storage (Per-Tenant)                  ││
│  │  ┌────────┐ ┌────────┐ ┌────────┐                           ││
│  │  │ videos │ │ audios │ │transcripts│                        ││
│  │  └────────┘ └────────┘ └────────┘                           ││
│  │          Local (单机) / S3/OSS (生产)                        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
AliceLM/
├── apps/
│   ├── api/                    # FastAPI后端
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── videos.py
│   │   │   ├── chat.py
│   │   │   ├── wechat.py
│   │   │   └── stats.py
│   │   ├── services/           # 应用层服务（HTTP 语义）
│   │   │   ├── chat_service.py
│   │   │   └── video_service.py
│   │   └── dependencies.py
│   │
│   └── web/                    # Next.js前端
│       ├── app/
│       │   ├── page.tsx        # Dashboard
│       │   ├── chat/
│       │   ├── library/
│       │   ├── graph/
│       │   ├── timeline/
│       │   ├── tasks/
│       │   ├── console/
│       │   └── settings/
│       └── components/
│
├── alice/                      # ★ Alice 核心模块（新增）
│   ├── one/                    # Alice One 层
│   │   ├── identity.py         # AliceIdentityService
│   │   ├── context.py          # ContextAssembler
│   │   └── timeline.py         # TimelineService
│   │
│   ├── agent/                  # Agent 引擎
│   │   ├── core.py             # AliceAgentCore（统一入口）
│   │   ├── strategy.py         # StrategySelector + 各 Strategy
│   │   ├── task_planner.py     # TaskPlanner
│   │   ├── tool_executor.py    # ToolExecutor
│   │   ├── tool_router.py      # ToolRouter
│   │   ├── mcp_client.py       # MCP Client
│   │   ├── memory.py           # MemoryManager
│   │   └── tools/              # Tool 定义
│   │       ├── video_tools.py  # ask_video / search_videos 等
│   │       ├── graph_tools.py  # search_graph 等
│   │       ├── timeline_tools.py
│   │       ├── search_tools.py # deep_web_research
│   │       └── ext/            # 外部迁移工具
│   │           └── strands_like/
│   │               ├── basic.py
│   │               ├── http_web.py
│   │               └── unsafe.py
│   │
│   ├── control_plane/          # ★ 控制平面（配置中心）
│   │   ├── __init__.py         # 统一导出
│   │   ├── control_plane.py    # AliceControlPlane（统一入口）
│   │   ├── model_registry.py   # ModelRegistry（模型配置）
│   │   ├── prompt_store.py     # PromptStore（Prompt 管理）
│   │   ├── tool_registry.py    # ToolRegistry（工具注册）
│   │   ├── service_factory.py  # ServiceFactory（服务工厂）
│   │   └── types.py            # 共享类型定义
│   │
│   ├── search/                 # SearchAgent 服务
│   │   ├── search_agent.py     # SearchAgentService
│   │   └── web_client.py       # Web 搜索客户端封装
│   │
│   └── eval/                   # 评估模块
│       ├── eval_runner.py      # 评测执行器
│       └── eval_case.py        # 评测用例
│
├── services/
│   ├── watcher/                # 收藏夹监控服务
│   │   ├── __init__.py
│   │   ├── scanner.py
│   │   └── scheduler.py
│   │
│   ├── processor/              # 视频处理管道
│   │   ├── __init__.py
│   │   ├── downloader.py
│   │   ├── transcriber.py
│   │   └── pipeline.py
│   │
│   ├── asr/                    # ASR模型适配层
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── whisper_local.py
│   │   ├── faster_whisper.py
│   │   └── api_provider.py     # 云端 ASR 统一接口
│   │
│   ├── ai/                     # AI服务（Provider 层）
│   │   ├── __init__.py
│   │   ├── llm/                # LLM Provider
│   │   ├── rag/                # RAG Provider
│   │   ├── summarizer.py
│   │   └── embedder.py
│   │
│   ├── knowledge/              # 知识图谱服务
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   └── learning.py
│   │
│   ├── mcp/                    # MCP Server（对外暴露能力）
│   │   ├── __init__.py
│   │   ├── server.py
│   │   └── tools.py
│   │
│   └── notifier/               # 通知服务
│       ├── __init__.py
│       └── wechat.py
│
├── packages/
│   ├── db/                     # 数据库模块
│   │   ├── models/
│   │   │   ├── tenant.py
│   │   │   ├── video.py
│   │   │   ├── agent.py        # AgentRun / AgentStep
│   │   │   ├── timeline.py     # TimelineEvent
│   │   │   └── eval.py         # EvalCase / EvalResult
│   │   ├── crud.py
│   │   └── migrations/
│   │
│   ├── queue/                  # 任务队列
│   │   ├── tasks.py
│   │   └── worker.py
│   │
│   └── config/                 # 配置管理
│       ├── settings.py
│       └── .env.example
│
├── config/                     # ★ ControlPlane 配置中心
│   ├── models.yaml             # 模型配置 (LLM/Embedding/ASR profiles)
│   ├── prompts.yaml            # Prompt 配置 (系统人格/任务专用)
│   ├── tools.yaml              # 工具配置 (工具列表/场景默认)
│   └── services.yaml           # 服务配置 (Provider 实现)
│
├── third_party/                # ★ 开源参考仓库（新增，gitignore）
│   ├── mindsearch/             # MindSearch clone
│   ├── openmanus/              # OpenManus clone
│   ├── gemini_cli/             # Gemini CLI clone
│   └── strands_agents_tools/   # strands-agents/tools clone
│
├── scripts/
│   ├── scan_favlist.py
│   └── migrate.py
│
├── data/                       # 数据目录（gitignore）
│   ├── videos/
│   ├── audio/
│   ├── transcripts/
│   └── db.sqlite
│
├── docs/
│   ├── README.md                 # 文档索引
│   ├── strategy/                 # 路线图与审计
│   │   ├── ROADMAP.md
│   │   └── ai_project_audit/
│   ├── architecture/             # 架构/标准
│   │   ├── DESIGN.md
│   │   ├── BACKEND_ARCHITECTURE.md
│   │   ├── FRONTEND_ARCHITECTURE.md
│   │   └── DESIGN_SYSTEM.md
│   ├── product/                  # PRD
│   │   ├── PRD.md
│   │   └── PRD_FRONTEND.md
│   ├── operations/               # 部署/流程
│   │   ├── DEPLOYMENT.md
│   │   └── PR_WORKFLOW.md
│   ├── api/                      # API 规格
│   ├── research/                 # 调研/专项
│   │   ├── AGENT_RESEARCH.md
│   │   └── MULTI_SOURCE_REFACTOR.md
│   └── archive/                  # 历史
│       └── ALICE_VISION_ANALYSIS.md
│
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

### 2.3 Alice One 与 Agent 分层架构

本小节在前面整体架构的基础上，明确 Alice One 与 Agent 引擎在系统中的位置、
分层关系以及与现有模块/数据的交互方式。

#### 2.3.1 分层视图

```text
┌─────────────────────────────────────────────────────────────┐
│                         Clients                             │
│  Web UI / 微信Bot / MCP / CLI / 其他入口                   │
└───────────────┬────────────────────────────────────────────┘
                │ HTTP / WebSocket / MCP
                ▼
┌─────────────────────────────────────────────────────────────┐
│       API Gateway + Routers (apps/api/routers)             │
│  videos / chat / folders / auth / config ...               │
└───────────────┬────────────────────────────────────────────┘
                │ 调用应用服务（Application Services）        
                ▼
┌─────────────────────────────────────────────────────────────┐
│   Application Services (apps/api/services)                  │
│   VideoService / ChatService / FolderService / ...         │
└───────────────┬────────────────────────────────────────────┘
                │ 面向用例，封装 HTTP 语义                   
                │ 统一通过 Alice One 层获取人格 + 上下文       
                ▼
┌─────────────────────────────────────────────────────────────┐
│                Alice One Layer (alice/one)                 │
│   • AliceIdentityService    # 人格 & 工具配置              │
│   • ContextAssembler        # 上下文装配                   │
│   • TimelineService         # 统一时间线                   │
└───────────────┬────────────────────────────────────────────┘
                │ 构造 AgentTask + 上下文                     
                ▼
┌─────────────────────────────────────────────────────────────┐
│             Agent Engine (alice/agent)                     │
│   • AliceAgentCore         # 统一入口 + ReAct 循环        │
│   • ToolRouter + tools/    # 工具路由与执行               │
└───────────────┬────────────────────────────────────────────┘
                │ 通过工具访问领域服务                       
                ▼
┌─────────────────────────────────────────────────────────────┐
│     Domain & Integration Services (services/*)             │
│   ai / knowledge / processor / asr / notifier / mcp ...   │
└───────────────┬────────────────────────────────────────────┘
                │ 使用基础设施（DB/队列/配置/RAGFlow/文件）   
                ▼
┌─────────────────────────────────────────────────────────────┐
│     Infrastructure & Data (packages/*, data/*, Chroma…)    │
└─────────────────────────────────────────────────────────────┘
```

关键约束：

- Alice One 层不直接处理 HTTP 或前端状态，只面向应用服务和 Agent 引擎。
- Agent 引擎不直接访问数据库，只通过工具调用现有 `services/ai`、`services/knowledge` 等模块。
- Watcher / Processor / ASR / Notifier / RAGFlow 等原有模块保持职责不变，
  被 Alice One + Agent 作为「能力提供者」组合使用，而不是被重写。

#### 2.3.2 数据视图（Alice One 依赖的数据）

Alice One 不引入新的「平行世界」数据表，而是对现有表做视图化：

- **TenantProfile（逻辑视图）**
  - 来源：`Tenant` + `TenantConfig` 中 `alice.*` 命名空间下的配置
  - 内容：persona 名称/语气、语言、verbosity、可用工具集合、偏好设置
  - 形式：Pydantic/数据类模型，不新增主表，避免与 TenantConfig 重复存储

- **TimelineEvent（统一时间线）**
  - 基于 `LearningRecord` 扩展语义，抽象为「某时间点发生的一件事」：
    - `event_type`: watch_video / ask_question / highlight / insight / plan_created ...
    - `scene`: chat / library / video / graph / timeline / tasks / console
    - `context`: JSON，包含视频/概念/对话 ID 等上下文
  - 所有入口（Web / 微信 / MCP）在关键动作结束后都调用 `TimelineService.append_event`，
    把行为写入同一张事件表，形成一条统一时间线。

- **PersonaSnapshot（派生视图）**
  - 从 TimelineEvent + 视频/概念/对话中「汇总」出一段时间内的用户画像：
    - 主题分布（最近常看的领域）
    - 问题模式（规划类 / 怀疑类等比例）
    - 兴趣/观点变化（从 A → B）
  - 初期可按需实时计算；如有性能压力，再落一个缓存表，明确标为物化视图而非主事实表。

#### 2.3.3 Alice One 三大服务职责

- **AliceIdentityService**
  - 输入：`tenant_id`、`user_id`（可选）、`scene`
  - 输出：
    - `system_prompt`：Alice One 的人格与行为规则
    - `tool_scopes`：在当前场景允许使用的工具 scope 列表
    - `settings`：语言、语气、输出风格等
    - `tenant_profile`：合并后的 TenantProfile 视图

- **TimelineService**
  - `append_event(event)`：统一写入时间线事件
  - `query(user_id, period, filters)`：按时间/类型/场景查询事件
  - `summarize(user_id, period)`：基于事件生成 PersonaSnapshot

- **ContextAssembler**
  - 输入：`AgentTask`（tenant/user/scene/query/video_id/前端附加上下文）
  - 内部组合：最近对话 + RAG 检索到的相关视频片段 + 知识图谱概念 + 精简 PersonaSnapshot
  - 输出：
    - `messages`：已经拼装好、可直接发送给 LLM/Agent 的 messages 列表
    - `citations`：所有引用的视频片段/概念/时间线事件，前端可以统一渲染为引用卡片

#### 2.3.3.x Agent 核心数据类定义

以下数据类贯穿 Alice One + Agent 各模块，是 Claude 实现时的"合同"：

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

class Scene(str, Enum):
    CHAT = "chat"
    RESEARCH = "research"
    TIMELINE = "timeline"
    LIBRARY = "library"
    VIDEO = "video"
    GRAPH = "graph"
    TASKS = "tasks"
    CONSOLE = "console"

@dataclass
class AgentTask:
    """Agent 的统一输入契约"""
    tenant_id: str
    scene: Scene                          # 当前场景
    query: str                            # 用户输入
    user_id: Optional[str] = None
    video_id: Optional[int] = None        # 关联视频（若有）
    selection: Optional[str] = None       # 用户选中的文本
    extra_context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentCitation:
    """引用来源"""
    type: str                             # video / concept / timeline / web
    id: str
    title: str
    snippet: str
    url: Optional[str] = None

@dataclass
class AgentStep:
    """Agent 执行的单个步骤（用于调试 / 回放）"""
    step_idx: int
    thought: str                          # LLM 的思考
    tool_name: Optional[str] = None
    tool_args: Optional[Dict] = None
    observation: Optional[str] = None
    error: Optional[str] = None

@dataclass
class AgentResult:
    """Agent 的统一输出契约"""
    answer: str
    citations: List[AgentCitation] = field(default_factory=list)
    steps: List[AgentStep] = field(default_factory=list)  # 可选
    token_usage: Optional[Dict[str, int]] = None
```

#### 2.3.4 典型请求链路（以 Chat 为例）

1. 前端 `/home/chat` 向 `/api/chat` 发送请求：
   - body 中包含 `scene="chat"`，可选 `video_id` / 选中文本 / graph 节点等附加上下文。
2. `chat` 路由校验参数后调用 `ChatService`。
3. `ChatService` 构造 `AgentTask`，调用：
   - `AliceIdentityService` 获取 Alice One 的人格与工具范围
   - `ContextAssembler` 组装短期 / 中期 / 长期上下文
4. 将 `AgentTask` + 上下文交给 `AliceAgentCore.run_task(task)`：
   - 基于 `tool_scopes` 从 `ToolRouter` 获取可用工具
   - 运行 ReAct 循环：LLM 思考 → 选择工具 → 执行 → 追加 observation
5. 得到 `AgentResult` 后：
   - `ChatService` 通过 `TimelineService.append_event` 记录 ask_question 等事件
   - Router 将 `{ answer, citations, steps? }` 返回前端。

其他入口（微信 / MCP / 视频详情页 / Graph 页面）仅在 **scene 和附加上下文** 不同，
后续链路全部复用这一套 Alice One + Agent 流程。

#### 2.3.4.x AliceAgentCore 内部结构与 Strategy

上一节的 `AgentOrchestrator` 在实际实现中统一升级为 **AliceAgentCore**，
作为 Agent 引擎的唯一入口，内部包含以下子组件：

```text
┌───────────────────────────────────────┐
│           AliceAgentCore              │
├───────────────────────────────────────┤
│  • StrategySelector                   │
│  • TaskPlanner                        │
│  • ToolExecutor (ReAct loop)          │
│  • ToolRouter                         │
│  • MemoryManager                      │
│  • ResultCritic (可选)                │
└───────────────────────────────────────┘
```

- **StrategySelector**：根据 `scene` + 简单意图识别，选择合适的执行策略：
  - `ChatStrategy`：偏对话、解释和轻量问答，不启用重型工具；
  - `ResearchStrategy`：偏深度检索 / 多轮推理，启用 `deep_web_research` 等工具；
  - `TimelineStrategy`：偏「自我变化 / 学习轨迹」类问题，优先走 TimelineService / Graph；
  - 未来可扩展：`PlanStrategy`（任务规划）、`ReflectionStrategy`（自我复盘）等。

- **TaskPlanner**：将自然语言任务拆成多个 step 的规划器，输出 `AgentPlan`。

- **ToolExecutor**：执行 ReAct 循环（LLM 思考 → 调用工具 → 注入观察 → 继续思考），支持最大步数控制与错误处理。

- **ToolRouter**：统一管理本地 Tool 和外部 MCP Tool 的调用分发。

- **MemoryManager**：管理短期对话记忆与长期上下文（对接 ContextAssembler）。

- **ResultCritic**（可选）：对 Agent 输出做自我校验，发现明显错误时重试或修正。

**核心接口（伪代码）：**

```python
class AliceAgentCore:
    async def run_task(self, task: AgentTask) -> AgentResult:
        strategy = self.strategy_selector.pick(task)       # chat / research / timeline / ...
        context  = self.memory_manager.build_context(task)
        plan     = self.task_planner.plan(task, context, strategy)
        result   = self.tool_executor.execute(plan, task, context, self.tool_router, strategy)
        self.result_critic.review(task, result, strategy)  # 可选
        return result
```

**设计约束：**

- 不存在多个 Engine；所有入口场景（chat / library / video / graph / timeline / tasks / console）最终都通过 `AliceAgentCore.run_task()` 处理。
- `web_search` / `deep_web_research` 等能力都被视为 Tool，由 TaskPlanner 决定是否使用。
- 将来从开源项目迁移的 Planner / Executor 逻辑会被重命名为 Alice 自己的 TaskPlanner / ToolExecutor，实现细节不暴露第三方工程名。

#### 2.3.5 Tools 与 Provider 的关系

上层的 **Tool** 与底层的 **Provider** 分层如下：

- Tool（由 `ToolRouter` 管理）：
  - 面向 AliceAgentCore 暴露：`name` / `description` / `input_schema` / `output_schema` / `scope`。
  - handler 内部只调用领域服务，例如 `QAService`、`KnowledgeGraphService`、`TimelineService` 等。
  - Agent 只看到 "ask_video" / "search_videos" / "search_graph" 这类语义化工具，不关心用的是哪家云、哪种模型。

- Provider（在 `services/ai`、`services/asr`、`packages/config` 中）：
  - 例如：`LLMProvider`、`ASRProvider`、`EmbeddingProvider`、`RAGProvider`。
  - 通过租户级 `TenantConfig` 中的 `llm.*` / `asr.*` / `rag.*` 配置选择具体实现：
    - LLM: OpenAI / Claude / DeepSeek / 本地 Ollama ...
    - ASR: Whisper 本地 / Faster-Whisper / 讯飞 / 阿里 / OpenAI Whisper API ...
    - RAG: RAGFlow / Chroma（降级）

这层分离带来的效果：

- **切换底层 Provider 时**：只改配置（或 Provider 层实现），Tool 和 Agent 行为保持稳定。
- **新增一种 Provider 时**：只需要在 Provider 层注册新的实现，不需要改 Agent 脑子。
- **多租户差异化**：不同租户可以配置不同 provider / 模型，但用的仍然是相同的工具集合。

#### 2.3.6 容错与降级策略

Alice One + Agent 层对错误的处理策略：

- **Tool 调用级错误**（单个工具失败）：
  - 工具 handler 内捕获领域服务抛出的异常，转化为结构化 observation，例如：
    - `{ "error": "RAGFlow timeout", "fallback": "chroma" }`
  - AliceAgentCore 仍然把这个 observation 作为一步 `AgentStep` 记录下来，
    既方便调试，也允许后续尝试其它工具或向用户解释失败原因。

- **Provider 级降级**：
  - RAG：优先走 RAGFlow，当 RAGFlow 不可用或超时时，自动降级到本地 Chroma（见 `config/rag.yaml` 的 `fallback` 字段）。
  - LLM：如果某个租户配置的主模型不可用，可在 Provider 层定义备用模型（例如从 gpt-4o 降级到 gpt-4o-mini）。
  - ASR：长视频或指定语言时，按规则自动切换到更合适的 Provider（已有的 `asr.auto_switch` 机制）。

- **Agent 级防御**：
  - 为 Agent 循环设置：
    - 最大步数（MAX_STEPS），防止死循环。
    - 总超时（per-run timeout），防止单次请求拖垮系统。
  - 当连续多次工具调用失败时，Agent 直接生成「失败解释」回答，并提示用户稍后重试或改写问题。

通过这些策略，Alice One 能在底层组件不稳定时，尽可能给出可解释的结果，
而不是直接在用户体验层面“静默失败”。

#### 2.3.7 多入口统一契约与前端集成

所有入口（Web / 微信 / MCP / 未来移动端）与后端的统一契约是 `AgentTask`：

- 必填字段：`tenant_id`、`scene`、`query`
- 可选字段：`user_id`、`video_id`、`selection`（选中文本/节点）、`extra_context`（前端特有信息）

前端的职责是根据当前页面路由和用户操作，正确构造这些字段；
后端从不关心「这个请求来自哪种 UI」，只关心：这是哪个租户、在哪个场景、在问什么问题。

这保证了：

- 新增一个入口（比如 VSCode 插件）时，只要能按约定构造 `AgentTask`，就可以立刻复用 Alice One + Agent 全链路。
- 前端只需要实现统一的结果渲染（answer + citations + steps?），而不需要为每个入口定制问答/检索逻辑。

#### 2.3.8 与 ROADMAP / AGENT_RESEARCH 的对应关系

本设计与愿景/研究文档中的规划一一对应（`1204PLAN.md` 已归档删除，当前路线图见 `docs/strategy/ROADMAP.md`，调研见 `docs/research/AGENT_RESEARCH.md`）：

- **ROADMAP / Alice One 能力层**：
  - AliceIdentityService ≈ 「Alice 身份 / 人格」服务
  - TimelineService ≈ 「统一时间线」与事件记录
  - ContextAssembler ≈ 「上下文拼装器」，负责从知识、时间线、对话中抽取合适的信息给 Alice One 使用

- **AGENT_RESEARCH 中的简化 Agent 建议**：
  - 采用自建简化版 ReAct 循环（AgentOrchestrator），而不是一上来引入复杂 Agent 框架；
  - 以 OpenAI Function Calling 为工具调用协议，由 ToolRouter 把领域服务包装成工具；
  - 通过 AgentRun / AgentStep / EvalCase 的数据结构，为后续评估与可观测性打基础。

换句话说：当前 DESIGN 中的 Alice One + Agent 架构，就是将 vision 文档里的规划
落实为「可落地的分层代码结构」，而不是停留在概念层的「大图」。

#### 2.3.9 Tools / Service / Provider / MCP 分层规范

> 目的：把「Alice One + Agent」层和现有 backend 分层统一起来，  
> 避免以后所有东西都往 Tool/MCP 里塞，变成不可维护的微内核地狱。

##### 一、一句话定义

- **Service**：Alice 真·会做的事  
  下载、转写、分析、检索、图谱、时间线、通知……所有真实业务流程和资源操作都在这里完成。

- **Tool**：把 Service（或其他能力）做成「LLM 可调用的按钮」  
  给 Agent/LLM 看的一层，有 `name / description / parameters` schema，内部只调 Service。

- **MCP**：一种"远程工具协议"  
  - 我去用别人的 MCP 工具（Alice 作为 MCP Client）  
  - 我把自己的能力暴露为 MCP 工具（Alice 作为 MCP Server）  

在架构层面，MCP 只是能力来源的一种形式，最终都被包装成 Tool 供 Agent 使用。

---

##### 二、内部世界：前端 / Agent 如何用自家 Service / Tool

内部从上到下的调用链，对应现有代码目录：

1. **前端 / Clients**
   - Web（apps/web）、未来的微信、CLI、Claude Desktop（通过 MCP）等。
   - 只调用 HTTP / WebSocket，不感知 Tool / Service 细节。

2. **API Gateway + 会话 / 鉴权（apps/api/routers）**
   - 例如 `/api/chat`、`/api/agent/*` 等路由。
   - 负责认证、租户解析、基础异常处理。

3. **Conversation / Task API（apps/api/services 中的应用层 Service）**
   - 把 HTTP 请求转成内部 DTO / AgentTask：
     - 如：`ChatService` / `AgentTaskService`。
   - 面向业务：这是一条 Chat 请求？还是一个 Agent 任务？

4. **Alice One 层（alice/one/*）**
   - Alice One 实现位于 `alice/one/`，通过 Application Services (apps/api/services) 对外暴露。
   - **AliceIdentityService** (`alice/one/identity.py`)：  
     从 `TenantConfig.alice.*` 生成 persona / 工具白名单 / 场景信息。
   - **ContextAssembler** (`alice/one/context.py`)：  
     基于 AgentTask + 历史对话 + 向量检索 + 图谱 + Timeline 拼装 messages + 初始上下文。

5. **AliceAgentCore（Agent 大脑，alice/agent）**
   - 只认两件事：
     - 一个支持 function calling 的 LLM；
     - 一组可用的 Tools（来自 ToolRouter）。
   - 负责单 Agent ReAct 循环：
     - LLM 输出 thought + tool_calls；
     - 顺序执行 Tool；
     - 收集 observation，再喂回 LLM。
   - **不允许**在这里直接调用 VideoService / QAService / Provider / MCP Client。

6. **Tool Layer（按钮层，alice/agent/tools/*）**
   - 对 LLM/Agent 暴露的每一个「按钮」：
     - `search_videos`
     - `get_video_detail`
     - `ask_knowledge`
     - `compare_videos`
     - `timeline_query`
     - `generate_report`
     - 等。
   - 一个 Tool handler 的职责：
     - 解析 + 校验 LLM 传入的参数；
     - 调用一个或多个 **领域 Service**（services/*）；
     - 把返回值转成干净、结构化的 JSON 结果。

7. **Service Layer（本事层，services/*）**
   - 真正干活的业务实现：
     - `services/watcher`：收藏夹扫描、任务下发；
     - `services/processor`：下载 / 抽音频 / ASR / 文本预处理；
     - `services/asr`：对接不同 ASR Provider；
     - `services/ai`：RAG / 问答 / 摘要 / 报告；
     - `services/knowledge`：概念抽取 / 知识图谱操作；
     - `alice/one`：AliceIdentityService / ContextAssembler / TimelineService；
     - `alice/search`：SearchAgentService（深度 Web 搜索 / 多源聚合逻辑）；
     - `services/notifier`：通知渠道；
     - ……
   - **注**：SearchAgentService 核心实现位于 `alice/search/search_agent.py`，供 `deep_web_research` Tool 调用。  
   - 可以是长耗时、有副作用（写 DB / 写文件 / 调外部 API），通过队列 / Scheduler 驱动。

8. **Provider / 基础设施层**
   - `packages/rag`、`packages/db`、`services/ai` 内部的 Provider、外部 API：
     - RAGFlow / ChromaDB / Qdrant；
     - OpenAI / Claude / DeepSeek；
     - Whisper / 其他 ASR API；
     - 文件存储 / DB；
     - 未来的 MCP Client（外部 MCP Servers）。
   - 不包含业务语义，专注「如何连」「怎么调用」「怎么降级」。

---

##### 三、视频分析任务的归属

- **Pipeline 分析（下载 / 转写 / 分析 / 向量化）：一律归 Service，不归 Tool**
  - 由 `services/downloader`、`services/processor`、`services/asr` 等负责；
  - 任务调度和重试通过队列 / Scheduler 处理；
  - 特点：耗时长、IO 密集、错误/重试逻辑复杂。

- **Tool 只做两件事：读结果 + 排队**
  - 读结果类 Tool：
    - `ask_video` / `search_videos` / `compare_videos` / `summarize_range` 等：
      - 只读取 Video / Transcript / Summary / Concept / 向量 / 图谱等已有数据；
      - 不触发完整处理 Pipeline。
  - 控制类 Tool（如需 Agent 触发处理）：
    - `request_video_analysis(video_id)`：
      - 内部只向队列推送一个任务 ID；
      - 返回 `task_id/status`，不在 Tool 中同步跑完全部流程。

---

##### 四、MCP 在架构中的位置

1. **Alice 作为 MCP Server（对外暴露能力）**
   - 在 `services/mcp` 中，把一部分内部 Tool/Service 暴露为 MCP 工具：
     - 例如：`search_videos`, `ask_knowledge`, `get_timeline_summary` 等。
   - 外部 Agent 调用路径：
     - MCP Tool（外部视角）→ 我们的 MCP Server → 内部 Tool → Service → Provider。
   - 规范：对外 MCP 不引入新业务模型，只是现有能力的协议包装。

2. **Alice 作为 MCP Client（消费外部 MCP 能力，未来扩展）**
   - 外部 MCP Server 被视为一种 Provider：
     - 由 MCP Client 封装连接 / 鉴权 / 协议；
     - 封装在某个 Service 里（如 `WebSearchService`、`NotionService`、`GithubService`）。
   - 内部 Tool 调用这些 Service，就像调用本地 Service 一样：
     - 对 Agent/LLM 而言，只是多了一些 Tool：
       - `web_search` / `notion_search` / `github_search_repo` …
   - 关键点：**Agent 不感知"是不是 MCP"，只看到平坦的 tools[] 列表**。

---

##### 五、设计铁律（约束）

1. **铁律 1：Service 写实事，Tool 只做适配**
   - 所有真实业务流程、资源操作、一致性约束，都写在 Service / Job / Pipeline 层；
   - Tool 只负责：
     - 解析参数；
     - 调用 Service；
     - 整理结果给 LLM。

2. **铁律 2：AliceAgentCore 只认 Tool + LLM**
   - AliceAgentCore 中禁止直接调用 Service / Provider / MCP Client；
   - 所有能力都必须通过 Tool 暴露。

3. **铁律 3：长耗时 / 重副作用逻辑不得出现在 Tool / Agent 层**
   - 下载、ASR、Embedding、批量分析等，必须在 Service/Job 层完成；
   - Tool 最多只触发「排队」或「查看进度」。

4. **铁律 4：Tool 不直接碰 Provider**
   - Provider（OpenAI / Claude / ASR / RAGFlow / MCP Client 等）只能被 Service 使用；
   - Tool 只能调 Service；
   - 降级 / 重试 / 监控逻辑全部在 Service / Provider 层解决。

5. **铁律 5：MCP 是 Tool 的实现细节，不是新架构层**
   - 不在 Agent 层出现「这是 MCP 工具 / 那是本地工具」的分支；
   - 注册到 Agent 的就是统一的 `tools[]` 列表，背后由 Local Service 或 MCP Provider 实现；
   - 这样即便大规模引入外部 MCP，整体架构复杂度仍然可控。

---

##### 六、SearchAgent 与深度 Web 搜索

为了支持「像人一样上网查资料」的能力，系统内部实现一个 **SearchAgentService**，并通过 Tool 暴露给 Agent。

**对 Agent 而言**：只看到一个 Tool：`deep_web_research`。

**其 handler 内部实现多步流程**：

1. **QueryInterpreter**：理解 / 重写用户问题，提取核心意图；
2. **QueryDecomposer**：生成多个子查询（针对不同角度或信息源）；
3. **WebFetcher**：对每个子查询执行 Web 搜索 + 抓取网页正文；
4. **PageAnalyzer**：从网页中抽取结论 / 关键句 / 元数据；
5. **EvidenceAggregator**：对多源结果去重 / 聚合；
6. **AnswerSynthesizer**：用 LLM 生成综合回答 + 引用列表。

**调用关系**：

```text
AliceAgentCore
  └─(ResearchStrategy)─> TaskPlanner 计划使用 deep_web_research
                          └─ ToolExecutor 调用 ToolRouter.deep_web_research()
                              └─ SearchAgentService.run(...)  # 多步搜索/聚合
```

**设计要点**：

- **SearchAgent 是 Service + Tool 的组合，不是新的 Engine**；
- 内部采用「多子查询 → 多路检索 → 聚合证据 → 综合回答」的模式（参考 MindSearch 等公开研究），
  但对 Agent 来说只是一个 `deep_web_research` Tool；
- 这套流程的实现会参考当前公开研究（如多 Agent Web 搜索 / 拆解-检索-聚合范式），
  但在代码结构和命名上完全内化为 Alice 自己的模块，不暴露第三方工程名；
- 深度 Web 搜索属于 **Service 层**能力，对 Agent 暴露为 Tool；
  Agent 与 Provider 不直接交互，只通过 Tool 调用 Service，由 Service 再调用底层 HTTP / MCP Client / 抓取逻辑。

---

##### 七、ControlPlane（控制平面）

**目标**：为 Alice 提供统一的配置中心，管理模型、Prompt、工具、服务的生命周期。

**核心组件**：

```
AliceControlPlane (统一入口)
├── ModelRegistry    # 模型配置：LLM/Embedding/ASR profiles
├── PromptStore      # Prompt 管理：系统人格/任务专用
├── ToolRegistry     # 工具注册：工具列表/场景默认
└── ServiceFactory   # 服务工厂：Provider 实现配置
```

**配置文件**（位于 `config/` 目录）：

| 文件 | 内容 |
|------|------|
| `models.yaml` | 模型 profiles + 任务默认映射 |
| `prompts.yaml` | Prompt 文本 + key 规范 |
| `tools.yaml` | 工具定义 + 场景默认工具集 |
| `services.yaml` | 服务配置 + Provider 实现 |

**关键能力**：

1. **模型解析**：`cp.resolve_model(task_type)` → 返回包含 provider/model/api_key 的 ResolvedModel
2. **LLM 创建**：`await cp.create_llm_for_task(task_type)` → 返回配置好的 ChatAI 实例
3. **Prompt 获取**：`await cp.get_prompt(key, user_id)` → 返回生效的 Prompt（含用户覆盖）
4. **工具列表**：`cp.list_tools_for_scene(scene)` → 返回场景可用工具名列表

**HTTP API**（`/api/v1/control-plane/*`）：

| 端点 | 用途 |
|------|------|
| `GET /models` | 列出所有模型 profiles |
| `GET /models/resolve` | 查看某任务实际使用的模型 |
| `GET /tools` | 列出场景可用工具 |
| `GET /prompts` | 列出 Prompt keys |
| `GET /summary` | 控制平面状态摘要 |

**使用示例**：

```python
from alice.control_plane import get_control_plane

cp = get_control_plane()

# 获取模型
llm = await cp.create_llm_for_task("chat")

# 获取 Prompt
prompt = await cp.get_prompt("chat", user_id=user.id)

# 获取场景工具
tools = cp.list_tools_for_scene("research")
```

---
## 3. 数据模型

### 3.1 数据库架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    Relational DB (SQLite/PostgreSQL)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐     │
│  │   Tenant    │──┬──►│    User     │      │   Config    │     │
│  │  (租户表)   │  │   │  (用户表)   │      │  (配置表)   │     │
│  └─────────────┘  │   └─────────────┘      └─────────────┘     │
│                   │                                             │
│                   │   ┌─────────────┐      ┌─────────────┐     │
│                   ├──►│   Video     │◄────►│    Tag      │     │
│                   │   │  (视频表)   │      │  (标签表)   │     │
│                   │   └──────┬──────┘      └─────────────┘     │
│                   │          │                                  │
│                   │          ▼                                  │
│                   │   ┌─────────────┐      ┌─────────────┐     │
│                   ├──►│WatchedFolder│      │TimelineEvent│     │
│                   │   │ (监控收藏夹)│      │ (时间线事件)│     │
│                   │   └─────────────┘      └─────────────┘     │
│                   │                                             │
│                   │   ┌─────────────────────────────────────┐  │
│                   │   │         Agent & Eval 相关表         │  │
│                   │   ├─────────────────────────────────────┤  │
│                   ├──►│ AgentRun   │ AgentStep │ AgentResult│  │
│                   │   │ (运行记录) │ (执行步骤)│ (运行结果) │  │
│                   │   ├─────────────────────────────────────┤  │
│                   └──►│ EvalCase   │ EvalResult│            │  │
│                       │ (评测用例) │ (评测结果)│            │  │
│                       └─────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Vector DB (ChromaDB/Qdrant)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Collection: {tenant_id}_video_chunks                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  id | video_id | chunk_idx | content | embedding | metadata ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Collection: {tenant_id}_concepts                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  id | name | description | embedding | related_videos       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **注**：`LearningRecord` 演进为 `TimelineEvent`，新增 `event_type` / `scene` / `context` 字段，
> 详见 ROADMAP Phase B 任务。

### 3.2 多租户与用户模型

```python
# packages/db/models/tenant.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

class TenantPlan(enum.Enum):
    FREE = "free"           # 免费版
    PRO = "pro"             # 专业版
    TEAM = "team"           # 团队版
    ENTERPRISE = "enterprise"  # 企业版

class Tenant(Base):
    """租户/组织"""
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    slug = Column(String(50), unique=True, index=True)  # 唯一标识符
    
    # 订阅计划
    plan = Column(Enum(TenantPlan), default=TenantPlan.FREE)
    plan_expires_at = Column(DateTime, nullable=True)
    
    # 配额限制
    max_videos = Column(Integer, default=100)         # 最大视频数
    max_storage_gb = Column(Integer, default=10)      # 最大存储GB
    max_users = Column(Integer, default=1)            # 最大用户数
    
    # 状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    users = relationship("User", back_populates="tenant")
    videos = relationship("Video", back_populates="tenant")
    configs = relationship("TenantConfig", back_populates="tenant")


class UserRole(enum.Enum):
    OWNER = "owner"         # 所有者
    ADMIN = "admin"         # 管理员
    MEMBER = "member"       # 成员
    VIEWER = "viewer"       # 只读

class User(Base):
    """用户"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    
    # 基本信息
    email = Column(String(255), unique=True, index=True)
    username = Column(String(50))
    password_hash = Column(String(255), nullable=True)  # 可选，支持OAuth
    
    # 第三方绑定
    wechat_openid = Column(String(100), nullable=True, index=True)
    bilibili_uid = Column(String(50), nullable=True)
    bilibili_sessdata = Column(Text, nullable=True)  # 加密存储
    
    # 角色与权限
    role = Column(Enum(UserRole), default=UserRole.MEMBER)
    
    # 状态
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    tenant = relationship("Tenant", back_populates="users")
    learning_records = relationship("LearningRecord", back_populates="user")


class TenantConfig(Base):
    """租户配置"""
    __tablename__ = "tenant_configs"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    
    key = Column(String(100))   # 配置键
    value = Column(Text)        # 配置值 (JSON)
    
    # 配置类型
    # asr_provider, asr_config, llm_provider, llm_config,
    # notify_channels, watched_folders, etc.
    
    tenant = relationship("Tenant", back_populates="configs")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'key', name='uq_tenant_config'),
    )
```

### 3.3 核心业务模型（租户隔离）

```python
# packages/db/models/video.py

class VideoStatus(enum.Enum):
    PENDING = "pending"           # 待处理
    DOWNLOADING = "downloading"   # 下载中
    TRANSCRIBING = "transcribing" # 转写中
    ANALYZING = "analyzing"       # AI分析中
    DONE = "done"                 # 完成
    FAILED = "failed"             # 失败

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)  # 租户隔离
    
    # 视频信息
    bvid = Column(String(20), index=True)
    title = Column(String(500))
    author = Column(String(100))
    duration = Column(Integer)  # 秒
    cover_url = Column(String(500))
    source_url = Column(String(500))
    source_type = Column(String(20), default="bilibili")  # bilibili/youtube/local
    
    # 处理状态
    status = Column(Enum(VideoStatus), default=VideoStatus.PENDING)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # 文件路径（相对于租户目录）
    video_path = Column(String(500), nullable=True)
    audio_path = Column(String(500), nullable=True)
    transcript_path = Column(String(500), nullable=True)
    
    # AI生成内容
    summary = Column(Text, nullable=True)
    key_points = Column(Text, nullable=True)        # JSON
    concepts = Column(Text, nullable=True)          # JSON
    
    # 处理配置（覆盖租户默认）
    asr_provider = Column(String(50), nullable=True)
    llm_provider = Column(String(50), nullable=True)
    
    # 时间戳
    collected_at = Column(DateTime)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # 关系
    tenant = relationship("Tenant", back_populates="videos")
    tags = relationship("VideoTag", back_populates="video")
    
    # 复合唯一约束：同一租户下bvid唯一
    __table_args__ = (
        UniqueConstraint('tenant_id', 'bvid', name='uq_tenant_video'),
        Index('ix_tenant_status', 'tenant_id', 'status'),
    )


class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    category = Column(String(50))  # 领域分类
    
    videos = relationship("VideoTag", back_populates="tag")


class VideoTag(Base):
    __tablename__ = "video_tags"
    
    video_id = Column(Integer, ForeignKey("videos.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)
    confidence = Column(Float, default=1.0)  # AI标签置信度
    
    video = relationship("Video", back_populates="tags")
    tag = relationship("Tag", back_populates="videos")


class WatchedFolder(Base):
    """监控的收藏夹"""
    __tablename__ = "watched_folders"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)  # 租户隔离
    
    folder_id = Column(String(50))
    folder_type = Column(String(20))  # favlist / season / subscription
    name = Column(String(200))
    platform = Column(String(20), default="bilibili")  # bilibili / youtube
    
    last_scan_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'folder_id', name='uq_tenant_folder'),
    )


class LearningRecord(Base):
    """学习记录"""
    __tablename__ = "learning_records"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    video_id = Column(Integer, ForeignKey("videos.id"))
    
    action = Column(String(20))  # viewed / asked / reviewed / exported
    duration = Column(Integer, nullable=True)  # 学习时长（秒）
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(Text, nullable=True)  # JSON额外数据
    
    user = relationship("User", back_populates="learning_records")
```

### 3.4 RAG设计（基于RAGFlow）

#### 为什么选择RAGFlow
| 特性 | RAGFlow | 自建方案 |
|------|---------|----------|
| 文档解析 | ✅ 内置多格式解析 | 需自己实现 |
| 智能分块 | ✅ 语义分块 | 需调参 |
| 多种检索 | ✅ 混合检索(向量+关键词) | 需组合 |
| 知识库管理 | ✅ 完整UI | 需自建 |
| 多租户 | ✅ 原生支持 | 需实现 |
| 部署 | ✅ Docker一键部署 | 复杂 |

#### 架构集成

```
┌─────────────────────────────────────────────────────────────────┐
│                      AliceLM                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│  │  Processor  │────►│  RAGFlow    │◄────│  AI Agent   │       │
│  │  (转写文本)  │     │  (知识库)   │     │  (问答)     │       │
│  └─────────────┘     └──────┬──────┘     └─────────────┘       │
│                             │                                   │
│                             ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    RAGFlow Server                           ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        ││
│  │  │ Dataset │  │ Chunking│  │Embedding│  │ Retrieval│        ││
│  │  │ (租户)  │  │ (分块)  │  │ (向量化)│  │ (检索)   │        ││
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        ││
│  │                         │                                   ││
│  │                         ▼                                   ││
│  │  ┌─────────────────────────────────────────────────────────┐││
│  │  │  Elasticsearch + Minio + MySQL (RAGFlow内置)            │││
│  │  └─────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### RAGFlow客户端封装

```python
# packages/rag/ragflow_client.py

import httpx
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class RAGFlowConfig:
    base_url: str = "http://localhost:9380"
    api_key: str = ""

@dataclass
class SearchResult:
    chunk_id: str
    content: str
    score: float
    metadata: dict
    source_video_id: int

class RAGFlowClient:
    """RAGFlow API客户端"""
    
    def __init__(self, config: RAGFlowConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={"Authorization": f"Bearer {config.api_key}"}
        )
    
    # ========== 数据集(Dataset)管理 ==========
    
    async def create_dataset(self, tenant_id: str, name: str) -> str:
        """为租户创建知识库"""
        resp = await self.client.post("/api/v1/dataset", json={
            "name": f"tenant_{tenant_id}_{name}",
            "description": f"AliceLM知识库 - 租户{tenant_id}",
            "embedding_model": "BAAI/bge-large-zh-v1.5",
            "chunk_method": "naive",  # 或 "qa", "manual"
            "parser_config": {
                "chunk_token_count": 512,
                "layout_recognize": False,  # 纯文本无需布局识别
            }
        })
        return resp.json()["data"]["id"]
    
    async def get_or_create_dataset(self, tenant_id: str) -> str:
        """获取或创建租户知识库"""
        dataset_name = f"tenant_{tenant_id}_videos"
        
        # 查询是否存在
        resp = await self.client.get("/api/v1/dataset", params={
            "name": dataset_name
        })
        datasets = resp.json().get("data", [])
        
        if datasets:
            return datasets[0]["id"]
        
        return await self.create_dataset(tenant_id, "videos")
    
    # ========== 文档管理 ==========
    
    async def upload_transcript(
        self, 
        tenant_id: str,
        video_id: int,
        title: str,
        transcript: str,
        metadata: dict
    ) -> str:
        """上传视频转写文本到知识库"""
        dataset_id = await self.get_or_create_dataset(tenant_id)
        
        # 构建文档内容（带元数据）
        document_content = f"""# {title}

## 视频信息
- 视频ID: {video_id}
- 作者: {metadata.get('author', '')}
- 时长: {metadata.get('duration', 0)}秒

## 转写内容
{transcript}
"""
        
        # 上传文档
        resp = await self.client.post(
            f"/api/v1/dataset/{dataset_id}/document",
            files={"file": (f"video_{video_id}.txt", document_content, "text/plain")},
            data={
                "parser_id": "naive",  # 使用朴素分块
                "run": "1"  # 立即解析
            }
        )
        return resp.json()["data"]["id"]
    
    async def delete_document(self, tenant_id: str, video_id: int):
        """删除视频对应的文档"""
        dataset_id = await self.get_or_create_dataset(tenant_id)
        
        # 查找文档
        resp = await self.client.get(
            f"/api/v1/dataset/{dataset_id}/document",
            params={"keywords": f"video_{video_id}"}
        )
        docs = resp.json().get("data", [])
        
        for doc in docs:
            await self.client.delete(
                f"/api/v1/dataset/{dataset_id}/document/{doc['id']}"
            )
    
    # ========== 检索与问答 ==========
    
    async def search(
        self,
        tenant_id: str,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.2
    ) -> List[SearchResult]:
        """语义检索"""
        dataset_id = await self.get_or_create_dataset(tenant_id)
        
        resp = await self.client.post(
            f"/api/v1/dataset/{dataset_id}/retrieval",
            json={
                "question": query,
                "top_k": top_k,
                "similarity_threshold": similarity_threshold,
                "rerank_model": "BAAI/bge-reranker-v2-m3",  # 可选重排
            }
        )
        
        results = []
        for chunk in resp.json().get("data", {}).get("chunks", []):
            # 从chunk内容中提取video_id
            video_id = self._extract_video_id(chunk.get("content", ""))
            results.append(SearchResult(
                chunk_id=chunk["id"],
                content=chunk["content"],
                score=chunk["similarity"],
                metadata=chunk.get("metadata", {}),
                source_video_id=video_id
            ))
        
        return results
    
    async def chat(
        self,
        tenant_id: str,
        question: str,
        conversation_id: Optional[str] = None
    ) -> dict:
        """RAG对话（使用RAGFlow内置对话能力）"""
        dataset_id = await self.get_or_create_dataset(tenant_id)
        
        # 创建或获取对话
        if not conversation_id:
            resp = await self.client.post("/api/v1/conversation", json={
                "dataset_ids": [dataset_id],
                "llm_model": "gpt-4o-mini",  # 可配置
                "prompt": self._get_system_prompt()
            })
            conversation_id = resp.json()["data"]["id"]
        
        # 发送消息
        resp = await self.client.post(
            f"/api/v1/conversation/{conversation_id}/message",
            json={"content": question}
        )
        
        return {
            "conversation_id": conversation_id,
            "answer": resp.json()["data"]["content"],
            "references": resp.json()["data"].get("references", [])
        }
    
    def _get_system_prompt(self) -> str:
        return """你是一个学习助手，基于用户收藏的视频内容回答问题。
        
规则：
1. 只基于提供的视频内容回答，不要编造
2. 引用具体视频来源
3. 如果内容中没有相关信息，明确告知用户
4. 用简洁清晰的语言回答"""
    
    def _extract_video_id(self, content: str) -> int:
        """从内容中提取video_id"""
        import re
        match = re.search(r'视频ID:\s*(\d+)', content)
        return int(match.group(1)) if match else 0
```

#### RAGFlow部署配置

```yaml
# docker-compose.ragflow.yml
version: '3.8'

services:
  ragflow:
    image: infiniflow/ragflow:latest
    container_name: ragflow
    ports:
      - "9380:9380"  # API
      - "9443:443"   # Web UI
    environment:
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_USER=root
      - MYSQL_PASSWORD=ragflow
      - MYSQL_DB=ragflow
      - MINIO_HOST=minio:9000
      - ES_HOST=elasticsearch:9200
    volumes:
      - ./data/ragflow:/ragflow/data
    depends_on:
      - mysql
      - elasticsearch
      - minio

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ragflow
      MYSQL_DATABASE: ragflow
    volumes:
      - ./data/mysql:/var/lib/mysql

  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - ./data/es:/usr/share/elasticsearch/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - ./data/minio:/data
```

#### 配置示例

```yaml
# config/rag.yaml
rag:
  provider: "ragflow"  # ragflow / chroma (fallback)
  
  ragflow:
    base_url: "http://localhost:9380"
    api_key: "${RAGFLOW_API_KEY}"
    
    # 分块配置
    chunk_method: "naive"
    chunk_token_count: 512
    
    # Embedding模型
    embedding_model: "BAAI/bge-large-zh-v1.5"
    
    # 重排模型（可选）
    rerank_model: "BAAI/bge-reranker-v2-m3"
    
    # 检索配置
    default_top_k: 5
    similarity_threshold: 0.2
  
  # 降级方案
  fallback:
    provider: "chroma"
    persist_directory: "./data/chroma"
```

### 3.5 数据隔离策略

| 层级 | 隔离方式 | 说明 |
|------|----------|------|
| **关系数据库** | tenant_id字段 | 所有业务表包含tenant_id，查询时自动过滤 |
| **RAGFlow** | 独立Dataset | 每租户独立知识库：`tenant_{id}_videos` |
| **文件存储** | 目录隔离 | `data/{tenant_id}/videos/`, `data/{tenant_id}/audio/` |
| **缓存** | Key前缀 | Redis key格式：`{tenant_id}:{key}` |
| **任务队列** | 队列分组 | 可按租户优先级调度 |

```python
# packages/db/tenant_context.py

from contextvars import ContextVar
from sqlalchemy.orm import Query

# 当前租户上下文
current_tenant: ContextVar[int] = ContextVar('current_tenant')

class TenantQuery(Query):
    """自动添加租户过滤的Query"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def _add_tenant_filter(self):
        tenant_id = current_tenant.get(None)
        if tenant_id and hasattr(self._entity_zero().entity, 'tenant_id'):
            return self.filter_by(tenant_id=tenant_id)
        return self

# 中间件自动设置租户上下文
async def tenant_middleware(request, call_next):
    tenant_id = get_tenant_from_request(request)  # 从JWT/header获取
    token = current_tenant.set(tenant_id)
    try:
        response = await call_next(request)
        return response
    finally:
        current_tenant.reset(token)
```

### 3.6 ER图

```
┌─────────────────┐       ┌─────────────────┐
│     Video       │       │      Tag        │
├─────────────────┤       ├─────────────────┤
│ id              │       │ id              │
│ bvid            │       │ name            │
│ title           │       │ category        │
│ status          │       └────────┬────────┘
│ summary         │                │
│ key_points      │                │
│ ...             │                │
└────────┬────────┘       ┌────────┴────────┐
         │                │    VideoTag     │
         │                ├─────────────────┤
         ├────────────────│ video_id        │
         │                │ tag_id          │
         │                │ confidence      │
         │                └─────────────────┘
         │
         │        ┌─────────────────────┐
         ├────────│  TranscriptChunk    │
         │        ├─────────────────────┤
         │        │ id                  │
         │        │ video_id            │
         │        │ content             │
         │        │ embedding           │
         │        └─────────────────────┘
         │
         │        ┌─────────────────────┐
         └────────│   LearningRecord    │
                  ├─────────────────────┤
                  │ id                  │
                  │ video_id            │
                  │ action              │
                  └─────────────────────┘
```

---

## 4. 核心模块设计

### 4.1 Watcher（监控服务）

```python
# services/watcher/scanner.py

class FolderScanner:
    """收藏夹扫描器"""
    
    def __init__(self, db: Session, queue: TaskQueue):
        self.db = db
        self.queue = queue
    
    async def scan_all_folders(self):
        """扫描所有监控的收藏夹"""
        folders = self.db.query(WatchedFolder).filter(
            WatchedFolder.is_active == True
        ).all()
        
        for folder in folders:
            await self.scan_folder(folder)
    
    async def scan_folder(self, folder: WatchedFolder):
        """扫描单个收藏夹，检测新视频"""
        # 获取收藏夹视频列表
        videos = await fetch_favlist(folder.folder_id)
        
        for video in videos:
            # 检查是否已存在
            exists = self.db.query(Video).filter(
                Video.bvid == video["bvid"]
            ).first()
            
            if not exists:
                # 创建新记录
                new_video = Video(
                    bvid=video["bvid"],
                    title=video["title"],
                    author=video["upper"],
                    duration=video["duration"],
                    status=VideoStatus.PENDING,
                    collected_at=datetime.utcnow()
                )
                self.db.add(new_video)
                self.db.commit()
                
                # 加入处理队列
                await self.queue.enqueue("process_video", {
                    "video_id": new_video.id,
                    "bvid": new_video.bvid
                })
        
        # 更新扫描时间
        folder.last_scan_at = datetime.utcnow()
        self.db.commit()
```

### 4.2 Processor（处理管道）

```python
# services/processor/pipeline.py

class VideoPipeline:
    """视频处理管道"""
    
    def __init__(self, db: Session, ai: AIService, notifier: Notifier):
        self.db = db
        self.ai = ai
        self.notifier = notifier
    
    async def process(self, video_id: int):
        """处理视频的完整流程"""
        video = self.db.query(Video).get(video_id)
        
        try:
            # Step 1: 下载
            video.status = VideoStatus.DOWNLOADING
            self.db.commit()
            video.video_path = await self.download(video.bvid)
            
            # Step 2: 提取音频
            video.audio_path = await self.extract_audio(video.video_path)
            
            # Step 3: 转写
            video.status = VideoStatus.TRANSCRIBING
            self.db.commit()
            transcript = await self.transcribe(video.audio_path)
            video.transcript_path = await self.save_transcript(transcript)
            
            # Step 4: AI分析
            video.status = VideoStatus.ANALYZING
            self.db.commit()
            
            analysis = await self.ai.analyze(transcript, video.title)
            video.summary = analysis["summary"]
            video.key_points = json.dumps(analysis["key_points"])
            video.concepts = json.dumps(analysis["concepts"])
            
            # Step 5: 向量化存储
            await self.create_embeddings(video, transcript)
            
            # Step 6: 自动打标签
            tags = await self.ai.suggest_tags(analysis)
            await self.apply_tags(video, tags)
            
            # 完成
            video.status = VideoStatus.DONE
            video.processed_at = datetime.utcnow()
            self.db.commit()
            
            # Step 7: 发送通知
            await self.notifier.notify_complete(video)
            
        except Exception as e:
            video.status = VideoStatus.FAILED
            video.error_message = str(e)
            self.db.commit()
            raise
```

### 4.3 AI Agent

```python
# services/ai/summarizer.py

class Summarizer:
    """AI摘要生成"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    async def analyze(self, transcript: str, title: str) -> dict:
        """分析视频内容"""
        
        prompt = f"""
        你是一个学习助手，请分析以下视频内容。
        
        视频标题：{title}
        
        转写文本：
        {transcript[:8000]}  # 限制长度
        
        请提供：
        1. 摘要（3句话以内，概括核心内容）
        2. 核心观点（3-5条，每条一句话）
        3. 关键概念（提取3-5个关键词/概念）
        4. 金句（如果有值得记住的精彩表达）
        
        以JSON格式返回。
        """
        
        response = await self.llm.chat(prompt)
        return json.loads(response)


# services/ai/qa.py

class QAService:
    """问答服务"""
    
    def __init__(self, db: Session, llm_client, embedder):
        self.db = db
        self.llm = llm_client
        self.embedder = embedder
    
    async def ask(self, question: str, video_id: int = None) -> str:
        """回答问题"""
        
        # 检索相关内容
        if video_id:
            # 针对特定视频
            chunks = await self.get_video_chunks(video_id, question)
        else:
            # 跨视频检索
            chunks = await self.semantic_search(question)
        
        context = "\n\n".join([c.content for c in chunks])
        
        prompt = f"""
        基于以下视频内容回答用户问题。
        
        相关内容：
        {context}
        
        用户问题：{question}
        
        请基于内容回答，如果内容中没有相关信息，请说明。
        """
        
        return await self.llm.chat(prompt)
    
    async def semantic_search(self, query: str, top_k: int = 5):
        """语义检索"""
        query_embedding = await self.embedder.embed(query)
        
        # 使用向量相似度检索
        chunks = self.db.query(TranscriptChunk).order_by(
            TranscriptChunk.embedding.cosine_distance(query_embedding)
        ).limit(top_k).all()
        
        return chunks
```

### 4.4 Notifier（通知服务）

```python
# services/notifier/wechat.py

class WeChatNotifier:
    """企业微信通知"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def notify_complete(self, video: Video):
        """视频处理完成通知"""
        
        key_points = json.loads(video.key_points)
        points_text = "\n".join([f"• {p}" for p in key_points[:3]])
        
        # 查找相关视频
        related = await self.find_related(video)
        related_text = ""
        if related:
            related_text = f"\n\n🔗 相关视频：{related[0].title}"
        
        message = f"""📺 新视频已处理完成

「{video.title}」
UP主: {video.author} | {video.duration // 60}分钟

📝 摘要:
{video.summary}

💡 核心观点:
{points_text}
{related_text}

回复数字继续:
1-详细笔记 2-提问 3-完整文稿"""
        
        await self.send(message)
    
    async def send(self, message: str):
        """发送消息"""
        payload = {
            "msgtype": "text",
            "text": {"content": message}
        }
        async with aiohttp.ClientSession() as session:
            await session.post(self.webhook_url, json=payload)
```

### 4.5 ASR适配层

```python
# services/asr/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TranscriptSegment:
    """转写片段"""
    start: float      # 开始时间（秒）
    end: float        # 结束时间（秒）
    text: str         # 转写文本
    confidence: float # 置信度

@dataclass  
class TranscriptResult:
    """转写结果"""
    text: str                        # 完整文本
    segments: List[TranscriptSegment] # 分段信息
    language: str                    # 检测到的语言
    duration: float                  # 音频时长

class ASRProvider(ABC):
    """ASR提供者抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """提供者名称"""
        pass
    
    @abstractmethod
    async def transcribe(
        self, 
        audio_path: str,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptResult:
        """执行转写"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查是否可用"""
        pass


# services/asr/whisper_local.py

class WhisperLocalProvider(ASRProvider):
    """本地Whisper模型"""
    
    name = "whisper_local"
    
    def __init__(self, model_size: str = "medium"):
        self.model_size = model_size
        self._model = None
    
    def _load_model(self):
        if self._model is None:
            import whisper
            self._model = whisper.load_model(self.model_size)
        return self._model
    
    async def transcribe(self, audio_path: str, language: str = None, **kwargs) -> TranscriptResult:
        model = self._load_model()
        result = model.transcribe(
            audio_path,
            language=language,
            **kwargs
        )
        return TranscriptResult(
            text=result["text"],
            segments=[
                TranscriptSegment(
                    start=s["start"],
                    end=s["end"],
                    text=s["text"],
                    confidence=s.get("confidence", 1.0)
                )
                for s in result["segments"]
            ],
            language=result["language"],
            duration=result["segments"][-1]["end"] if result["segments"] else 0
        )


# services/asr/faster_whisper.py

class FasterWhisperProvider(ASRProvider):
    """Faster-Whisper (CTranslate2优化版)"""
    
    name = "faster_whisper"
    
    def __init__(self, model_size: str = "medium", device: str = "auto"):
        self.model_size = model_size
        self.device = device
        self._model = None
    
    async def transcribe(self, audio_path: str, language: str = None, **kwargs) -> TranscriptResult:
        from faster_whisper import WhisperModel
        
        if self._model is None:
            self._model = WhisperModel(self.model_size, device=self.device)
        
        segments, info = self._model.transcribe(audio_path, language=language)
        segments_list = list(segments)
        
        return TranscriptResult(
            text=" ".join(s.text for s in segments_list),
            segments=[
                TranscriptSegment(
                    start=s.start, end=s.end, 
                    text=s.text, confidence=s.avg_logprob
                )
                for s in segments_list
            ],
            language=info.language,
            duration=info.duration
        )


# services/asr/__init__.py

class ASRManager:
    """ASR管理器 - 统一调度不同ASR提供者"""
    
    providers = {
        "whisper_local": WhisperLocalProvider,
        "faster_whisper": FasterWhisperProvider,
        "xunfei": XunfeiProvider,
        "aliyun": AliyunProvider,
        "openai_whisper": OpenAIWhisperProvider,
    }
    
    def __init__(self, config: dict):
        self.config = config
        self.default_provider = config.get("default_asr", "whisper_local")
        self._instances = {}
    
    def get_provider(self, name: str = None) -> ASRProvider:
        """获取ASR提供者实例"""
        name = name or self.default_provider
        
        if name not in self._instances:
            provider_class = self.providers.get(name)
            if not provider_class:
                raise ValueError(f"未知的ASR提供者: {name}")
            self._instances[name] = provider_class(**self.config.get(name, {}))
        
        return self._instances[name]
    
    async def transcribe(
        self, 
        audio_path: str, 
        provider: str = None,
        **kwargs
    ) -> TranscriptResult:
        """执行转写"""
        asr = self.get_provider(provider)
        return await asr.transcribe(audio_path, **kwargs)
```

### 4.6 MCP Server

```python
# services/mcp/server.py

from mcp.server import Server
from mcp.types import Tool, Resource

class AliceLMMCPServer:
    """AliceLM MCP Server"""
    
    def __init__(self, db: Session, qa_service: QAService):
        self.db = db
        self.qa = qa_service
        self.server = Server("alice-lm")
        self._register_tools()
        self._register_resources()
    
    def _register_tools(self):
        """注册MCP工具"""
        
        @self.server.tool()
        async def search_videos(query: str, limit: int = 5) -> list:
            """
            搜索视频知识库
            
            Args:
                query: 搜索关键词或问题
                limit: 返回结果数量
            
            Returns:
                匹配的视频列表，包含标题、摘要、相关度
            """
            results = await self.qa.semantic_search(query, top_k=limit)
            return [
                {
                    "video_id": r.video.id,
                    "bvid": r.video.bvid,
                    "title": r.video.title,
                    "summary": r.video.summary,
                    "relevance": r.score
                }
                for r in results
            ]
        
        @self.server.tool()
        async def get_video_detail(video_id: int = None, bvid: str = None) -> dict:
            """
            获取视频详细信息
            
            Args:
                video_id: 视频ID
                bvid: B站BV号
            
            Returns:
                视频详情，包含文稿、摘要、标签等
            """
            if bvid:
                video = self.db.query(Video).filter(Video.bvid == bvid).first()
            else:
                video = self.db.query(Video).get(video_id)
            
            if not video:
                return {"error": "视频不存在"}
            
            return {
                "id": video.id,
                "bvid": video.bvid,
                "title": video.title,
                "author": video.author,
                "summary": video.summary,
                "key_points": json.loads(video.key_points or "[]"),
                "transcript": self._load_transcript(video),
                "tags": [t.tag.name for t in video.tags]
            }
        
        @self.server.tool()
        async def ask_knowledge(
            question: str, 
            video_ids: list = None
        ) -> dict:
            """
            基于知识库回答问题
            
            Args:
                question: 用户问题
                video_ids: 限定搜索的视频范围（可选）
            
            Returns:
                AI回答及引用来源
            """
            answer = await self.qa.ask(question, video_ids)
            return {
                "answer": answer,
                "sources": [...]  # 引用的视频片段
            }
        
        @self.server.tool()
        async def get_related_videos(
            video_id: int = None, 
            concept: str = None,
            limit: int = 5
        ) -> list:
            """
            获取相关视频
            
            Args:
                video_id: 基于某视频查找相关
                concept: 基于某概念查找相关
                limit: 返回数量
            
            Returns:
                相关视频列表
            """
            if video_id:
                return await self._find_related_by_video(video_id, limit)
            elif concept:
                return await self._find_related_by_concept(concept, limit)
            return []
    
    def _register_resources(self):
        """注册MCP资源"""
        
        @self.server.resource("videos://list")
        async def list_videos() -> str:
            """视频列表资源"""
            videos = self.db.query(Video).filter(
                Video.status == VideoStatus.DONE
            ).all()
            return json.dumps([
                {"id": v.id, "title": v.title, "bvid": v.bvid}
                for v in videos
            ])
        
        @self.server.resource("videos://{video_id}/transcript")
        async def get_transcript(video_id: int) -> str:
            """视频文稿资源"""
            video = self.db.query(Video).get(video_id)
            if video and video.transcript_path:
                with open(video.transcript_path) as f:
                    return f.read()
            return ""
    
    async def run(self, transport="stdio"):
        """运行MCP服务"""
        await self.server.run(transport)


# 启动脚本: python -m services.mcp
if __name__ == "__main__":
    import asyncio
    server = AliceLMMCPServer(db, qa_service)
    asyncio.run(server.run())
```

#### MCP配置示例（Claude Desktop）

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "alice-lm": {
      "command": "python",
      "args": ["-m", "services.mcp"],
      "cwd": "/path/to/AliceLM"
    }
  }
}
```

---

## 5. API设计

### 5.1 RESTful API

```yaml
# Videos API
GET    /api/videos              # 获取视频列表
GET    /api/videos/:id          # 获取视频详情
POST   /api/videos/upload       # 上传本地视频
DELETE /api/videos/:id          # 删除视频

# Chat API
POST   /api/chat                # 问答
  body: { question: string, video_id?: number }
  response: { answer: string, sources: [] }

# Stats API
GET    /api/stats/overview      # 学习概览
GET    /api/stats/weekly        # 周报数据
GET    /api/stats/tags          # 标签分布

# Folders API
GET    /api/folders             # 获取监控的收藏夹
POST   /api/folders             # 添加收藏夹
DELETE /api/folders/:id         # 移除收藏夹

# WeChat Webhook
POST   /api/wechat/callback     # 接收微信消息
```

### 5.2 WebSocket（实时更新）

```javascript
// 处理进度实时推送
ws.on("video:progress", { video_id, status, progress })
ws.on("video:complete", { video_id, summary })
ws.on("video:failed", { video_id, error })
```

---

## 6. 技术选型

### 6.1 组件选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 后端框架 | FastAPI | 异步支持好、类型提示、自动文档 |
| 前端框架 | Next.js 14 | App Router、RSC、良好DX |
| 数据库 | SQLite | 轻量、无需部署、够用 |
| 向量数据库 | ChromaDB / SQLite-VSS | 嵌入式、易部署 |
| 任务队列 | APScheduler + asyncio | 轻量、Python原生 |
| LLM | OpenAI / Claude API | 主流、稳定 |
| 微信 | 企业微信Webhook | 稳定、官方支持 |
| MCP | mcp-python-sdk | 官方SDK、Claude原生支持 |

### 6.2 ASR模型选型

| 模型 | 速度 | 质量 | 成本 | 推荐场景 |
|------|------|------|------|----------|
| **Whisper (本地)** | ★★☆ | ★★★★ | 免费 | 默认选项、质量优先 |
| **Faster-Whisper** | ★★★★ | ★★★★ | 免费 | 批量处理、速度优先 |
| **讯飞ASR** | ★★★★★ | ★★★★ | 付费 | 中文优化、实时场景 |
| **阿里Paraformer** | ★★★★ | ★★★☆ | 免费 | 中文、本地部署 |
| **OpenAI Whisper API** | ★★★★★ | ★★★★★ | 付费 | 云端、不想本地部署 |

### 6.3 推荐配置

```yaml
# config/asr.yaml
asr:
  default: "faster_whisper"  # 默认使用Faster-Whisper平衡速度和质量
  
  whisper_local:
    model_size: "medium"
    device: "auto"
  
  faster_whisper:
    model_size: "medium"
    device: "auto"
    compute_type: "float16"
  
  xunfei:
    app_id: "${XUNFEI_APP_ID}"
    api_key: "${XUNFEI_API_KEY}"
  
  openai_whisper:
    api_key: "${OPENAI_API_KEY}"
    model: "whisper-1"
  
  # 自动切换规则
  auto_switch:
    enabled: true
    rules:
      - language: "zh"
        provider: "faster_whisper"  # 中文用Faster-Whisper
      - duration_gt: 3600
        provider: "faster_whisper"  # 长视频用Faster-Whisper加速
```

---

## 8. 部署架构

### 8.1 开发环境

```bash
# 启动后端
cd apps/api && uvicorn main:app --reload

# 启动前端
cd apps/web && npm run dev

# 启动Worker
python -m services.worker
```

### 8.2 生产环境

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: ./apps/api
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///data/db.sqlite
      - OPENAI_API_KEY=${OPENAI_API_KEY}
  
  web:
    build: ./apps/web
    ports:
      - "3000:3000"
    depends_on:
      - api
  
  worker:
    build: ./services
    volumes:
      - ./data:/app/data
    depends_on:
      - api
```

---

## 9. 开源代码迁移与内化规范（给 AI 助手看的）

> 本章节是写给 IDE 里的 AI 助手 / 开发代理的执行说明，  
> 目标是**加速开发**，但对外保持 Alice 的技术身份与命名空间统一。

### 9.1 总原则

1. **只借「内功」，不暴露品牌**
   - 允许从以下开源项目中拷贝 / 改写代码逻辑：
     - MindSearch（多 Agent Web 搜索范式）
     - OpenManus（通用 Agent 框架 / Flow / ReAct）
     - Gemini CLI（工具调用 / MCP 工程实践）
   - **禁止**在 Alice 对外 API / 日志 / 配置中出现上述项目名、原类名、原模块名。
   - 允许在内部注释里写明来源和链接，并保留原 License 说明。

2. **统一收纳到 Alice 命名空间**
   - 所有迁移后的代码必须放在 `alice/` 下的模块中，例如：
     - `alice/agent/task_planner.py`
     - `alice/agent/tool_executor.py`
     - `alice/search/search_agent.py`
   - 禁止在运行时代码中直接 `import openmanus` 或 `import mindsearch` 等。

3. **第三方仓库统一放在 `third_party/` 目录**
   - 结构示例：
     - `third_party/openmanus/`（完整 clone）
     - `third_party/mindsearch/`
     - `third_party/gemini_cli/`
     - `third_party/strands_agents_tools/`
   - 这些目录只作为「源码参考 / 临时依赖」，**不允许**从业务代码直接 import；
     只能由 AI 助手在迁移时读取和 copy 代码片段。

4. **迁移方式优先级**
   - 能用「**读代码 → 重写实现**」解决的，优先重写；
   - 为节省时间，允许「**直接拷贝函数 / 类 → 重命名 + 删改**」：
     - 拷贝后第一步：改成 Alice 命名；
     - 第二步：去掉 CLI / UI / demo 特有逻辑；
     - 第三步：把配置 / Provider 接入 Alice 的 Provider 抽象层。
   - 适配要求（所有拷贝/改写均需满足）：
     - 数据命名：使用 `source_type`+`source_id`，禁止再引入 `bvid`；租户/用户参数必须注入（tenant_id/user_id）。
     - 错误与日志：使用 `alice.errors` 定义的错误类型；禁止日志输出敏感信息（key/token）。
     - 配置与模型：统一走 ControlPlane / `config/base/`，禁止直接实例化 LLM/Provider。
     - 工具接口：对齐 `AliceTool`/`ToolRouter` 规范，补充安全级别/审计字段。
   - 已迁移的示例：`alice/agent/tools/ext/` 已参考 strands-agents/tools 的工具集实现，继续迁移时保持同样的适配规则。

---

### 9.2 MindSearch → SearchAgentService 迁移指令（给 AI）

目标：实现 `SearchAgentService` + `deep_web_research` Tool，让 Alice 具备「多子 query + 多路搜索 + 聚合回答」的能力。

**步骤说明（请 IDE / AI 助手执行）：**

1. **准备工作**
   - 在仓库根目录创建 `third_party/`（若不存在）：
     - `mkdir third_party`
   - Clone MindSearch：
     - `git clone https://github.com/InternLM/MindSearch.git third_party/mindsearch`

2. **定位核心搜索逻辑**
   - 在 `third_party/mindsearch` 里，重点关注：
     - `mindsearch/agent/` 目录下与 Web Planner / Web Searcher、查询拆解、网页抓取与摘要相关的 Python 文件；
   - 搜索以下关键词定位核心类 / 函数：
     - `"WebPlanner"` / `"WebSearcher"`
     - `"searcher_cfg"` / `"searcher_type"`
     - `"backend_example.py"`（作为调用示例）

3. **在 Alice 中创建 SearchAgent 模块**
   - 新建文件：`alice/search/search_agent.py`
   - 创建类（命名示例）：
     - `SearchAgentService`
     - `SearchPlan` / `SearchStep`
   - 在文件头部添加注释：
     ```python
     # 部分搜索规划与抓取逻辑参考了 MindSearch 项目 (Apache-2.0 License)
     # https://github.com/InternLM/MindSearch
     ```

4. **拷贝并改造逻辑（重点）**
   - 从 MindSearch 的相关 Python 文件中：
     - 拷贝「query 拆解」「多次调用搜索 API」「对网页结果做抽取和总结」的代码片段；
     - **禁止**拷贝 FastAPI app / CLI / 前端相关逻辑。
   - 同步重命名：
     - 所有类 / 函数改为 Alice 命名：例如 `WebPlanner` → `SearchPlanner`，`WebSearcher` → `SearchRunner`
     - 删除或替换掉所有 `MindSearch`、`mindsearch` 字样。
   - 修改依赖：
     - 使用 Alice 的 `Provider` 抽象来获取 LLM / HTTP Client；
     - 搜索引擎调用（DuckDuckGo / Bing / Brave 等）封装到 `alice/search/web_client.py` 中。

5. **以 Tool 形式对外暴露**
   - 在 `alice/agent/tools/search_tools.py` 中注册一个 Tool：
     - 名称：`deep_web_research`
     - 描述：执行多轮 Web 搜索和聚合，返回结构化搜索结果列表和总结。
   - 该 Tool 的 handler 内部调用：`SearchAgentService.run(query, user_context, max_steps=...)`

6. **对接 Strategy**
   - 在 `AliceAgentCore` 的 `ResearchStrategy` 中：
     - 将 `deep_web_research` 加入该 Strategy 的 Tool 白名单；
     - 在 Planner 的 prompt 里增加说明：「当问题需要查阅互联网最新信息时，优先调用 `deep_web_research`」。

---

### 9.3 OpenManus → TaskPlanner / ToolExecutor 迁移指令（给 AI）

目标：利用 OpenManus 的 Flow / ReAct Agent 思路，强化 Alice 的 Planner + Executor 实现。

1. **准备工作**
   - 在 `third_party/` 下 clone：
     - `git clone https://github.com/FoundationAgents/OpenManus.git third_party/openmanus`

2. **定位规划 & 执行核心**
   - 在 `third_party/openmanus` 中优先关注：
     - 根目录下的 `main.py`, `run_flow.py`, `run_mcp.py`；
     - `app/` 和 `workspace/` 目录中与 Agent 调度、Flow / TaskGraph 执行、Tool 调用循环相关的代码。
   - 搜索关键词：`"Flow"` / `"run_flow"` / `"agent"` / `"tool_call"` / `"ReAct"` 等。

3. **在 Alice 中创建 Planner / Executor 模块**
   - 新建 / 扩展文件：
     - `alice/agent/task_planner.py`
     - `alice/agent/tool_executor.py`
   - 文件头部加入注释，说明参考了该项目（保留链接和 License 简述）。

4. **拷贝并改写 Planner 逻辑**
   - 目标：得到一个 `TaskPlanner` 类：
     - `plan(task: AgentTask, context: AgentContext, strategy: Strategy) -> AgentPlan`
   - 从 OpenManus 中拷贝：
     - 将自然语言任务拆成多个 step 的 prompt 模板；
     - Flow / TaskGraph 的基本数据结构（节点 / 边 / 状态）。
   - 改写时注意：
     - 删除与原 UI / Terminal 交互相关的逻辑；
     - 将原先的「任务描述」结构统一映射到 Alice 的 `AgentTask` / `AgentPlan` 类型；
     - 所有类名、函数名使用 Alice 命名。

5. **拷贝并改写 Tool 执行循环**
   - 目标：得到一个 `ToolExecutor` 类：
     - `execute(plan, task, context, tool_router) -> AgentResult`
   - 从 OpenManus 中拷贝 / 改写：
     - ReAct 风格的「模型思考 → 调用工具 → 注入观察结果 → 继续思考」循环逻辑；
     - tool 调用错误处理（重试、失败中断）；
     - 最大步数控制 / 退出条件。
   - 把所有和「OpenManus」「Flow runner」相关的日志文案改写为「AliceAgentCore」。

6. **连接 AliceAgentCore**
   - 在 `AliceAgentCore` 初始化时：
     - 使用新的 `TaskPlanner` / `ToolExecutor` 实例；
     - 移除原来的临时 `AgentOrchestrator` 名字，统一改用 `AliceAgentCore`。

---

### 9.4 Gemini CLI → ToolRouter / MCPClient 迁移指令（给 AI）

目标：借用 Gemini CLI 的工具管理 / MCP 调用模式，完善 Alice 的 ToolRouter 和 MCP 集成。

1. **准备工作**
   - 在 `third_party/` 下 clone：
     - `git clone https://github.com/google-gemini/gemini-cli.git third_party/gemini_cli`

2. **定位核心工具 / MCP 逻辑**
   - 在 `third_party/gemini_cli` 中关注：
     - `packages/core` 目录：工具定义与注册、MCP 客户端、工具调用分发。
     - 文档 `docs/` 中关于 tools / MCP 的章节。

3. **在 Alice 中实现 ToolRouter**
   - 文件：`alice/agent/tool_router.py`
   - 实现目标接口：
     - `list_tool_schemas(task: AgentTask) -> List[ToolSchema]`
     - `execute(name: str, args: Dict) -> ToolResult`
   - 参考 Gemini CLI 的设计：
     - 每个工具有：name / description / parameters schema；
     - MCP 工具和本地工具在同一套抽象下被统一调用；
     - 对危险工具（shell / 文件写入）保留白名单与配置限制。

4. **实现 MCP Client**
   - 文件：`alice/agent/mcp_client.py`
   - 从 Gemini CLI 的 MCP 客户端实现中拷贝：
     - JSON-RPC 交互结构；
     - 工具列表获取；
     - 单次工具调用请求 / 响应处理。
   - 替换项：
     - 将所有项目名 / 日志中的 "Gemini CLI" 替换为内部名称（如：`McpClientInternal`）；
     - 把配置接入 Alice 的 Provider / Config 系统。

5. **在 DESIGN 中保持抽象，在实现中隐藏来源**
   - DESIGN 文档中只提：`ToolRouter` / `McpClient`；「支持 MCP 协议的外部工具」。
   - 不提 Gemini 相关具体实现名，相关说明只出现在代码注释中。

---

### 9.5 strands-agents/tools → Alice 通用工具迁移说明（给 AI 助手）

**1. 目标能力**

从 `strands-agents/tools` 迁移一批通用工具，用于 Alice 的 Tool 层，包括：

- **基础工具**：calculator, current_time, sleep, environment, journal
- **文件与 HTTP**：file_read, file_write, http_request
- **Web 搜索与抓取**：tavily_search / tavily_extract / tavily_crawl / tavily_map、exa_search / exa_get_contents
- **RSS / cron 等基础自动化**：rss, cron
- **（后续）高权限工具**：shell, python_repl, browser, use_computer 等（默认关闭）

这些工具将作为 Alice ToolRouter 的一个"通用工具包"，供不同 Strategy 选择使用。

**2. 仓库与 License**

- 仓库地址：`https://github.com/strands-agents/tools`
- License：Apache-2.0，允许商用和修改，保留版权与 NOTICE。

**3. 存放位置**

- clone 位置（只读参考，不直接 import）：`third_party/strands_agents_tools/`
- 迁移后的工具代码位置：`alice/agent/tools/ext/strands_like/`

**4. 重点文件（给 AI 的"看这里"列表）**

在 `third_party/strands_agents_tools/src/strands_tools/` 目录下，重点关注：

- **基础工具**：
  - `calculator.py`
  - `current_time.py`
  - `sleep.py`
  - `environment.py`
  - `journal.py`
- **文件与 HTTP**：
  - `file_read.py`
  - `file_write.py`
  - `http_request.py`
- **Web 搜索 / 抓取**：
  - `tavily.py`（tavily_search / tavily_extract / tavily_crawl / tavily_map）
  - `exa.py`（exa_search / exa_get_contents）
- **RSS / cron**：
  - `rss.py`
  - `cron.py`
- **（高风险工具，先迁代码、后期再打开）**：
  - `shell.py`
  - `python_repl.py`
  - `browser/__init__.py` / `browser/*.py`
  - `use_computer.py`
  - `code_interpreter.py`
  - `use_aws.py`
  - `slack.py`

**5. 在 Alice 中的落地位置与命名**

在 `alice/agent/tools/ext/strands_like/` 下创建对应模块：

- `basic.py` → 包装 calculator / current_time / sleep / environment / journal
- `files.py` → 包装 file_read / file_write
- `http_web.py` → 包装 http_request / tavily_* / exa_*
- `rss_cron.py` → 包装 rss / cron
- `unsafe.py` → 包装 shell / python_repl / browser / use_computer / use_aws / slack 等（默认不在工具白名单里）

每个模块内定义 **Alice 风格的 Tool 类**，统一实现：

```python
class AliceTool:
    name: str
    description: str
    parameters: Dict[str, Any]

    async def run(self, args: Dict[str, Any]) -> Any:
        ...
```

禁止在对外接口中直接使用 `strands_tools` 名字，只能出现在内部注释中。

**6. 具体拷贝 / 改写指令（给 AI 的操作步骤）**

以下步骤对每一个要迁移的工具模块执行一遍：

1. **创建目标文件**
   - 例如要迁移 `calculator.py`：
   - 在 `alice/agent/tools/ext/strands_like/basic.py` 中添加头部注释：
     ```python
     # 部分实现参考了 strands-agents/tools 中的 calculator.py (Apache-2.0)
     # https://github.com/strands-agents/tools
     ```

2. **阅读并拷贝核心逻辑**
   - 打开：`third_party/strands_agents_tools/src/strands_tools/calculator.py`
   - 找到：
     - 用来定义 calculator 工具的核心函数 / 类；
     - 输入参数解析、调用 sympy/数学库的部分。
   - 将相关逻辑拷贝到 `basic.py` 中的新类：
     ```python
     class CalculatorTool(AliceTool):
         name = "calculator"
         description = "Perform mathematical operations and symbolic math."
         parameters = {
             "type": "object",
             "properties": {
                 "expression": {"type": "string", "description": "Math expression to evaluate"},
             },
             "required": ["expression"],
         }

         async def run(self, args: Dict[str, Any]) -> Any:
             expression = args["expression"]
             # 这里粘贴并改写 strands_tools.calculator 的核心实现
             ...
     ```
   - 删除或改写：
     - 和 `strands.Agent`、`agent.tool.calculator(...)` 绑定的那部分；
     - 任何 CLI / 示例代码。

3. **接入 Alice 的 Provider / Config**
   - 如果工具需要外部服务（Tavily / Exa / AWS / Slack 等）：
     - 用 Alice 的 Config / Provider 系统读取环境变量，而不是使用 strands 自己的配置方式；
     - 例如在 `http_web.py` 里定义一个内部 client 工厂，从 Alice 的配置中读取 API key。

4. **在 ToolRouter 中注册**
   - 打开 `alice/agent/tool_router.py`，将新工具加入注册：
     ```python
     from alice.agent.tools.ext.strands_like.basic import CalculatorTool, CurrentTimeTool, SleepTool
     from alice.agent.tools.ext.strands_like.http_web import TavilySearchTool, TavilyExtractTool, ExaSearchTool, HttpRequestTool
     from alice.agent.tools.ext.strands_like.rss_cron import RssTool, CronTool
     ...

     DEFAULT_COMMON_TOOLS = {
         "calculator": CalculatorTool(),
         "current_time": CurrentTimeTool(),
         ...
     }
     ```
   - 在 Strategy 层控制哪些工具可见：
     - `ChatStrategy`：calculator / current_time / file_read（只读）
     - `ResearchStrategy`：tavily_* / exa_* / http_request / rss
     - 高危工具（shell / python_repl / browser / use_computer）只在 Console / Debug 场景开放且默认关闭。

5. **为每类工具添加最小测试**
   - 给每个文件加 1–2 个简单的单元测试或集成测试，例如：
     - calculator："sqrt(1764)" -> 42（与原 README 示例一致）
     - tavily_search：调用 mock client，返回固定结果；
     - file_read / file_write：在临时目录创建文件，读写成功。

**7. 安全与权限约束（非常重要）**

以下工具视为**高危工具**，只做代码迁移，不加入默认 Tool 白名单：

- `shell`（执行系统命令）
- `python_repl` / `code_interpreter`
- `browser`（自动操作浏览器）
- `use_computer`（桌面操作）
- `use_aws`（云资源操作）
- `slack`（对外发消息）

处理方式：

- 在 `alice/agent/tools/ext/strands_like/unsafe.py` 中先实现对应的 Tool 类；
- ToolRouter 默认不注册它们到任何 Strategy；
- 仅在 Console / 内部测试场景、并带显式确认下才启用。

**8. 与 SearchAgent 的关系**

- `TavilySearchTool` / `TavilyExtractTool` / `ExaSearchTool` 可直接被 `SearchAgentService` 内部调用；
- SearchAgentService 的多步搜索流程（来自 MindSearch 范式）+ 底层工具实现（来自 strands）= Alice 的完整 Web 搜索能力；
- 对外只暴露 `deep_web_research` Tool，内部组合使用这些底层工具。

**9. 后续扩展**

第二阶段可以考虑迁移：

- `memory.py` / `mem0_memory.py` / `mongodb_memory.py` / `elasticsearch_memory.py`，
  将其逻辑融合到 Alice 的 MemoryManager / Timeline / Graph 中，而不是平行留一套。
- 这些可以在 ROADMAP 的后续 Phase 中定义单独任务。

---

### 9.x 通用开源迁移模版（给未来的自己和 AI 助手）

> 当我们决定从一个新的开源项目迁移某些能力时，  
> 请为该项目单独新增一节「9.x.y XXX → Alice 模块迁移说明」，并按以下模版填写。

#### 9.x.y [项目名] → [Alice 内部模块名] 迁移说明

**1. 目标能力**
- 想从该项目获得什么能力？
- 在 Alice 里的目标模块是哪些？

**2. 仓库与 License**
- 仓库地址：`https://github.com/.../...`
- License 类型：MIT / Apache-2.0 / 等
- 要求：允许商用与修改；迁移后需在代码注释中保留来源与 License 声明。

**3. 存放位置**
- 克隆到本仓库的路径：`third_party/<project_name>/`
- 禁止：在业务代码中直接 `import <project_name>`。

**4. 需要重点参考 / 拷贝的模块（给 AI 的"看这里"列表）**
- 请列出需要重点阅读的目录 / 文件及简单说明。

**5. 在 Alice 中的落地位置**
- 对应的 Alice 模块路径及新类/函数名。

**6. 拷贝与改写规则（给 AI 助手的硬规则）**
- 拷贝后第一步：改成 Alice 命名；
- 第二步：去掉 CLI / UI / demo 特有逻辑；
- 第三步：把配置 / Provider 接入 Alice 的 Provider 抽象层；
- 禁止：将原项目名 / 类名暴露到对外 API、日志、前端字符串中。

**7. 测试与验收**
- 为迁移模块新增最小测试或验证步骤。
- 在 ROADMAP 对应 Phase 下增加一个勾选项。

---

> **总结给未来的 AI 助手一句话：**  
> 当你在实现 Alice 的 SearchAgent / TaskPlanner / ToolExecutor / ToolRouter / 通用工具时，  
> 允许你从 `third_party/mindsearch`、`third_party/openmanus`、`third_party/gemini_cli`、`third_party/strands_agents_tools` 中读取并拷贝代码，  
> 但 copy 后必须：
> - 改为 Alice 的模块 / 类名；
> - 删掉 UI / Demo 特有逻辑；
> - 接入 Alice 已有的 Provider / Config / Logging；
> - 不在对外接口中出现第三方项目名；
> - 高危工具（shell / python_repl / browser / use_computer 等）默认不启用。

---

*文档版本: v0.6*  
*最后更新: 2024-12-04*
